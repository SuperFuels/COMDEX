#!/usr/bin/env python3
"""
Tessaris Phase 26 - Resonant Analytics Layer (RAL)

Computes rolling harmonic averages, drift entropy, and stability metrics
from consolidated meta-resonant telemetry (MRTC).
"""

import json, time, math
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import asyncio
import websockets
import threading

# Paths
MRTC_PATH = Path("data/learning/meta_resonant_telemetry.jsonl")
RAL_LOG = Path("data/learning/ral_metrics.jsonl")
RAL_LOG.parent.mkdir(parents=True, exist_ok=True)

# WebSocket broadcast (optional)
CLIENTS = set()

# =========================================================
# ✅ FIX: include 'path' argument in the handler
# =========================================================
async def analytics_ws(websocket, path):
    """WebSocket endpoint for analytics clients (path-aware)."""
    print(f"📡 Client connected on {path}")
    CLIENTS.add(websocket)
    try:
        async for _ in websocket:
            pass  # keep connection alive
    except websockets.exceptions.ConnectionClosed:
        print("❌ Client disconnected from RAL stream")
    finally:
        CLIENTS.remove(websocket)


def read_recent_entries(n=50):
    """Read last N entries from MRTC JSONL."""
    if not MRTC_PATH.exists():
        return []
    with open(MRTC_PATH) as f:
        lines = f.readlines()[-n:]
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def compute_metrics(entries):
    """Compute rolling averages and drift metrics."""
    if not entries:
        return None

    nus, phis, amps = [], [], []
    for e in entries:
        try:
            rfc = e.get("rfc", {})
            rqfs = e.get("rqfs", {})
            nu = (rfc.get("nu_bias", 0.0) + rqfs.get("nu_bias", 0.0)) / 2
            phi = (rfc.get("phase_offset", 0.0) + rqfs.get("phase_offset", 0.0)) / 2
            amp = (rfc.get("amp_gain", 0.0) + rqfs.get("amp_gain", 0.0)) / 2
            nus.append(nu)
            phis.append(phi)
            amps.append(amp)
        except Exception:
            continue

    if not nus:
        return None

    mean_nu, mean_phi, mean_amp = np.mean(nus), np.mean(phis), np.mean(amps)
    drift_entropy = float(np.std([mean_nu, mean_phi, mean_amp]))
    stability = 1.0 / (1.0 + drift_entropy)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mean_nu": mean_nu,
        "mean_phi": mean_phi,
        "mean_amp": mean_amp,
        "drift_entropy": drift_entropy,
        "stability": stability,
    }


def run_analytics(interval=5.0):
    print("📈 Starting Tessaris Resonant Analytics Layer (RAL)...")

    # =========================================================
    # WebSocket server: run in its own thread with its own event loop
    # =========================================================
    def ws_thread():
        async def start_ws():
            async with websockets.serve(analytics_ws, "0.0.0.0", 8002):
                print("🌐 RAL WebSocket running on ws://0.0.0.0:8002/ws/analytics")
                await asyncio.Future()  # run forever

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_ws())
        loop.run_forever()

    threading.Thread(target=ws_thread, daemon=True).start()

    # =========================================================
    # Analytics computation loop
    # =========================================================
    while True:
        entries = read_recent_entries(100)
        metrics = compute_metrics(entries)
        if metrics:
            with open(RAL_LOG, "a") as f:
                f.write(json.dumps(metrics) + "\n")

            print(
                f"t={metrics['timestamp']} | ν={metrics['mean_nu']:+.4f} "
                f"φ={metrics['mean_phi']:+.4f} A={metrics['mean_amp']:+.4f} "
                f"S={metrics['stability']:.3f} H={metrics['drift_entropy']:.4f}"
            )

            # Broadcast to WebSocket clients safely
            for client in list(CLIENTS):
                try:
                    coro = client.send(json.dumps(metrics))
                    asyncio.run_coroutine_threadsafe(coro, asyncio.get_event_loop())
                except Exception:
                    pass
        else:
            print("⚠️ Waiting for telemetry data...")
        time.sleep(interval)


def main():
    run_analytics()


if __name__ == "__main__":
    main()