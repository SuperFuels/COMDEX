#!/usr/bin/env python3
"""
Tessaris Phase 26 - Resonant Analytics Layer (RAL)

Reads consolidated MRTC JSONL and computes rolling means + drift entropy,
then broadcasts via WS (websockets v12) on /ws/analytics.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import websockets

MRTC_PATH = Path("data/telemetry/meta_resonant_telemetry.jsonl")  # 'data' is your symlink ✅
RAL_LOG   = Path("data/learning/ral_metrics.jsonl")
RAL_LOG.parent.mkdir(parents=True, exist_ok=True)

WS_HOST = "0.0.0.0"
WS_PORT = 8002
WS_PATH = "/ws/analytics"

CLIENTS: set = set()

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _f(x, default: float = 0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float(default)

def read_recent_entries(n: int = 200) -> list[dict]:
    if not MRTC_PATH.exists():
        return []
    try:
        with MRTC_PATH.open("r", encoding="utf-8") as f:
            lines = f.readlines()[-n:]
    except Exception:
        return []
    out = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out

def compute_metrics(entries: list[dict]) -> dict | None:
    if not entries:
        return None

    nus, phis, amps = [], [], []
    fusion_s, fusion_h, fusion_c = [], [], []

    for e in entries:
        if not isinstance(e, dict):
            continue

        rqfs_fb = e.get("rqfs_feedback") if isinstance(e.get("rqfs_feedback"), dict) else {}
        aqci    = e.get("aqci") if isinstance(e.get("aqci"), dict) else {}
        aq_bias = aqci.get("bias") if isinstance(aqci.get("bias"), dict) else {}

        # Preferred (current MRTC): rqfs_feedback.{nu_bias, phi_bias, amp_bias}
        if any(k in rqfs_fb for k in ("nu_bias", "phi_bias", "amp_bias")):
            nu  = _f(rqfs_fb.get("nu_bias", 0.0))
            phi = _f(rqfs_fb.get("phi_bias", 0.0))
            amp = _f(rqfs_fb.get("amp_bias", 0.0))

        # Fallback (also present in your MRTC): aqci.bias.{nu_bias, phi_bias, amp_bias}
        elif any(k in aq_bias for k in ("nu_bias", "phi_bias", "amp_bias")):
            nu  = _f(aq_bias.get("nu_bias", 0.0))
            phi = _f(aq_bias.get("phi_bias", 0.0))
            amp = _f(aq_bias.get("amp_bias", 0.0))

        # Legacy fallback (older schemas)
        else:
            rfc  = e.get("rfc") if isinstance(e.get("rfc"), dict) else {}
            rqfs = e.get("rqfs") if isinstance(e.get("rqfs"), dict) else {}
            nu  = (_f(rfc.get("nu_bias", 0.0)) + _f(rqfs.get("nu_bias", 0.0))) / 2.0
            phi = (_f(rfc.get("phase_offset", 0.0)) + _f(rqfs.get("phase_offset", 0.0))) / 2.0
            amp = (_f(rfc.get("amp_gain", 0.0)) + _f(rqfs.get("amp_gain", 0.0))) / 2.0

        nus.append(nu); phis.append(phi); amps.append(amp)

        fusion = e.get("fusion") if isinstance(e.get("fusion"), dict) else {}
        if fusion:
            fusion_c.append(_f(fusion.get("fusion_coherence", 0.0)))
            fusion_s.append(_f(fusion.get("stability", 0.0)))
            fusion_h.append(_f(fusion.get("entropy", 0.0)))

    if not nus:
        return None

    mean_nu  = float(np.mean(nus))
    mean_phi = float(np.mean(phis))
    mean_amp = float(np.mean(amps))

    var_nu  = float(np.var(nus))
    var_phi = float(np.var(phis))
    var_amp = float(np.var(amps))
    drift_entropy = float(np.sqrt((var_nu + var_phi + var_amp) / 3.0))
    stability = float(1.0 / (1.0 + drift_entropy))

    out = {
        "type": "ral_metrics",
        "timestamp": _now(),
        "mean_nu": mean_nu,
        "mean_phi": mean_phi,
        "mean_amp": mean_amp,
        "drift_entropy": drift_entropy,
        "stability": stability,
        "mrtc_source": str(MRTC_PATH),
    }

    if fusion_c:
        out["fusion_coherence_mean"] = float(np.mean(fusion_c))
    if fusion_s:
        out["fusion_stability_mean"] = float(np.mean(fusion_s))
    if fusion_h:
        out["fusion_entropy_mean"] = float(np.mean(fusion_h))

    return out

# websockets v12 handler (single-arg)
async def analytics_ws(websocket):
    path = getattr(websocket, "path", None)
    if path is None and hasattr(websocket, "request"):
        path = websocket.request.path

    if path not in (WS_PATH, WS_PATH + "/"):
        await websocket.close(code=1008, reason="Unknown path")
        return

    print(f"📡 RAL client connected ({path})")
    CLIENTS.add(websocket)
    try:
        async for _ in websocket:
            pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        CLIENTS.discard(websocket)
        print("❌ RAL client disconnected")

async def broadcast(payload: dict):
    if not CLIENTS:
        return
    msg = json.dumps(payload)
    dead = []
    for ws in list(CLIENTS):
        try:
            await ws.send(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        CLIENTS.discard(ws)

async def run_analytics(interval: float = 2.0):
    print("📈 Starting Tessaris Resonant Analytics Layer (RAL)...")
    print(f"✅ Using MRTC file: {MRTC_PATH}")

    while True:
        entries = read_recent_entries(n=250)
        metrics = compute_metrics(entries)

        if metrics:
            with RAL_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(metrics) + "\n")

            print(
                f"t={metrics['timestamp']} | ν={metrics['mean_nu']:+.4f} "
                f"φ={metrics['mean_phi']:+.4f} A={metrics['mean_amp']:+.4f} "
                f"S={metrics['stability']:.3f} H={metrics['drift_entropy']:.6f}"
            )

            await broadcast(metrics)
        else:
            if not MRTC_PATH.exists():
                print("⚠️ Waiting for MRTC file…")
            else:
                print("⚠️ Waiting for telemetry data...")
        await asyncio.sleep(interval)

async def main():
    async with websockets.serve(
        analytics_ws, WS_HOST, WS_PORT,
        ping_interval=20, ping_timeout=20
    ):
        print(f"🌐 RAL WebSocket running on ws://{WS_HOST}:{WS_PORT}{WS_PATH}")
        await run_analytics()

if __name__ == "__main__":
    asyncio.run(main())