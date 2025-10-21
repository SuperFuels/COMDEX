#!/usr/bin/env python3
"""
Tessaris Phase 30.2 — Resonant Quantum Feedback Synchronizer (RQFS)
────────────────────────────────────────────────────────────────────
Receives adaptive bias packets from AQCI and applies live tuning to
the system’s resonance parameters.

Inbound :
    ws://localhost:8006/ws/rqfs_feedback     ←  AQCI

Outbound (optional future) :
    ws://localhost:8002/ws/analytics         →  RAL
    ws://localhost:8005/ws/fusion            →  TCFK

Publishes live feedback metrics for monitoring dashboards.
"""

import asyncio, json, math, websockets
from datetime import datetime, timezone
from pathlib import Path

RQFS_PORT   = 8006
LOG_PATH    = Path("data/control/rqfs_feedback.jsonl")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

CLIENTS = set()
feedback_state = {
    "nu_bias": 0.0,
    "phi_bias": 0.0,
    "amp_bias": 0.0,
    "resonant_phase": 0.0,
    "resonant_gain": 1.0,
    "timestamp": None,
}

# ─────────────────────────────────────────────
#  Feedback computation
# ─────────────────────────────────────────────
def update_feedback(bias):
    """Translate AQCI bias values into resonance adjustments."""
    feedback_state["nu_bias"]  = bias["nu_bias"]
    feedback_state["phi_bias"] = bias["phi_bias"]
    feedback_state["amp_bias"] = bias["amp_bias"]

    # Apply simple model for phase/gain modulation
    feedback_state["resonant_phase"] = (
        math.sin(bias["phi_bias"]) * 0.5 + 0.5
    )  # normalized 0–1
    feedback_state["resonant_gain"] = 1.0 + bias["amp_bias"] * 0.2

    feedback_state["timestamp"] = datetime.now(timezone.utc).isoformat()
    return feedback_state.copy()

# ─────────────────────────────────────────────
#  WebSocket server
# ─────────────────────────────────────────────
async def rqfs_ws(websocket):
    """Dashboard or monitor connections."""
    CLIENTS.add(websocket)
    print(f"🌐 RQFS client connected ({len(CLIENTS)} total)")
    try:
        await websocket.send(json.dumps({
            "type": "hello",
            "state": feedback_state,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))
        async for _ in websocket:
            pass
    except Exception as e:
        print(f"⚠️ RQFS client error: {e}")
    finally:
        CLIENTS.remove(websocket)
        print(f"🔻 RQFS client disconnected ({len(CLIENTS)} remaining)")

# ─────────────────────────────────────────────
#  Listener for AQCI → RQFS stream
# ─────────────────────────────────────────────
async def listen_aqci():
    uri = "ws://localhost:8004/ws/control"
    print(f"🧬 Listening for AQCI bias updates on {uri}")
    while True:
        try:
            async with websockets.connect(uri) as ws:
                async for msg in ws:
                    try:
                        data = json.loads(msg)
                        if data.get("type") == "adaptive_bias_update" or data.get("type") == "control_update":
                            bias = data["bias"]
                            new_state = update_feedback(bias)

                            with open(LOG_PATH, "a") as f:
                                f.write(json.dumps(new_state) + "\n")

                            print(
                                f"🌀 RQFS phase={new_state['resonant_phase']:.3f} "
                                f"gain={new_state['resonant_gain']:.3f} "
                                f"ν={bias['nu_bias']:+.4f} ϕ={bias['phi_bias']:+.4f} α={bias['amp_bias']:+.4f}"
                            )

                            if CLIENTS:
                                msg = json.dumps({
                                    "type": "feedback_update",
                                    "state": new_state
                                })
                                await asyncio.gather(*(c.send(msg) for c in list(CLIENTS)))
                    except Exception:
                        continue
        except Exception as e:
            print(f"⚠️ AQCI stream error: {e}, retrying…")
            await asyncio.sleep(3)

# ─────────────────────────────────────────────
#  Orchestration
# ─────────────────────────────────────────────
async def main():
    print("🔁 Starting Resonant Quantum Feedback Synchronizer (RQFS)…")
    await websockets.serve(rqfs_ws, "0.0.0.0", RQFS_PORT)
    print(f"🌐 RQFS running on ws://0.0.0.0:{RQFS_PORT}/ws/rqfs_feedback")
    await listen_aqci()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🧩 RQFS stopped.")