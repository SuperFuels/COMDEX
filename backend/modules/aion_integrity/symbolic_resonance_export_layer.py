#!/usr/bin/env python3
"""
Tessaris Phase 23 - Symbolic Resonance Export Layer (SREL)

Consumes:  <DATA_ROOT>/telemetry/meta_resonant_telemetry.jsonl
Produces:  <DATA_ROOT>/symatics/symbolic_resonance_stream.glyph
Serves WS: ws://0.0.0.0:8001/ws/symatics   (websockets v12)
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import websockets

ENV_DATA_ROOT = "TESSARIS_DATA_ROOT"

def pick_data_root() -> Path:
    import os
    if ENV_DATA_ROOT in os.environ:
        return Path(os.environ[ENV_DATA_ROOT]).expanduser()

    # prefer runtime-moved data
    rt = Path(".runtime")
    if rt.exists():
        # choose the first runtime data that has telemetry or control dirs
        for d in rt.glob("*/data"):
            if (d / "control").exists() or (d / "telemetry").exists():
                return d

    return Path("data")

DATA_ROOT = pick_data_root()

META_FILE = DATA_ROOT / "telemetry" / "meta_resonant_telemetry.jsonl"
OUT_DIR   = DATA_ROOT / "symatics"
OUT_FILE  = OUT_DIR / "symbolic_resonance_stream.glyph"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CLIENTS: set = set()

WS_HOST = "0.0.0.0"
WS_PORT = 8001
WS_PATH = "/ws/symatics"

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def fget(d: Optional[Dict[str, Any]], k: str, default: float = 0.0) -> float:
    if not isinstance(d, dict):
        return float(default)
    v = d.get(k, default)
    try:
        return float(v)
    except Exception:
        return float(default)

def glyph_from_params(nu: float, phi: float, amp: float) -> str:
    # ν bucket
    if abs(nu) < 0.5:
        base = "⊕"
    elif abs(nu) < 1.0:
        base = "⟲"
    else:
        base = "↔"

    # φ bucket
    if phi > 0.2:
        mod = "μ"
    elif phi < -0.2:
        mod = "∇"
    else:
        mod = "π"

    # amp bucket
    if amp > 6:
        energy = "💡"
    elif amp < 3:
        energy = "🌊"
    else:
        energy = "•"

    return f"{energy}{base}{mod}"

async def symatics_ws(websocket):
    path = getattr(websocket, "path", None)
    if path is None and hasattr(websocket, "request"):
        path = websocket.request.path

    if path not in (WS_PATH, WS_PATH + "/"):
        await websocket.close(code=1008, reason="Invalid path")
        return

    print(f"🪶 SREL client connected ({path})")
    CLIENTS.add(websocket)
    try:
        async for _ in websocket:
            pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        CLIENTS.discard(websocket)
        print("❌ SREL client disconnected")

async def broadcast(payload: Dict[str, Any]):
    if not CLIENTS:
        return
    msg = json.dumps(payload, ensure_ascii=False)
    dead = []
    for ws in list(CLIENTS):
        try:
            await ws.send(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        CLIENTS.discard(ws)

async def exporter_loop(interval: float = 1.0):
    print("🪶 Starting Tessaris Symbolic Resonance Export Layer (SREL)...")
    print(f"✅ DATA_ROOT = {DATA_ROOT}")
    print(f"✅ META_FILE = {META_FILE}")
    print(f"✅ OUT_FILE  = {OUT_FILE}")

    last_size = -1

    while True:
        if not META_FILE.exists():
            await asyncio.sleep(interval)
            continue

        try:
            size = META_FILE.stat().st_size
        except Exception:
            await asyncio.sleep(interval)
            continue

        if size != last_size:
            last_size = size
            try:
                with META_FILE.open("r", encoding="utf-8") as f:
                    lines = [l.strip() for l in f if l.strip()]
                if not lines:
                    await asyncio.sleep(interval)
                    continue
                entry = json.loads(lines[-1])
            except Exception:
                await asyncio.sleep(interval)
                continue

            rqfs_fb = entry.get("rqfs_feedback") if isinstance(entry, dict) else {}
            state   = rqfs_fb.get("state") if isinstance(rqfs_fb, dict) else {}

            nu  = fget(state, "nu_bias", 0.0)
            phi = fget(state, "phi_bias", 0.0)
            amp = fget(state, "amp_bias", 0.0)

            glyph = glyph_from_params(nu, phi, amp)

            out = {
                "type": "symatics",
                "timestamp": now_iso(),
                "nu": nu,
                "phi": phi,
                "amp": amp,
                "glyph": glyph,
            }

            with OUT_FILE.open("a", encoding="utf-8") as f:
                f.write(json.dumps(out, ensure_ascii=False) + "\n")

            print(f"🪶 t={out['timestamp']} | ν={nu:+.4f} φ={phi:+.4f} A={amp:+.4f} -> {glyph}")
            await broadcast(out)

        await asyncio.sleep(interval)

async def main():
    async with websockets.serve(symatics_ws, WS_HOST, WS_PORT, ping_interval=20, ping_timeout=20):
        print(f"🌐 SREL WebSocket running on ws://{WS_HOST}:{WS_PORT}{WS_PATH}")
        await exporter_loop()

if __name__ == "__main__":
    asyncio.run(main())