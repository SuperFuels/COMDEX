#!/usr/bin/env python3
"""
Tessaris Phase 30 — Adaptive Quantum Control Interface (AQCI)
──────────────────────────────────────────────────────────────
The AQCI forms the adaptive feedback layer in the Tessaris Resonant Stack.
It receives coherence-delta packets (Δ𝒞) from TCFK and continuously
adjusts the global bias parameters applied to RQFS and MRTC.

Core update law:
    ν_bias(t+1) = ν_bias(t) + kν · Δ𝒞
    ϕ_bias(t+1) = ϕ_bias(t) + kϕ · Δ𝒞
    α_bias(t+1) = α_bias(t) + kα · Δ𝒞

WebSocket roles:
    • Input  ←  ws://localhost:8005/ws/fusion (from TCFK)
    • Output →  ws://localhost:8006/ws/rqfs_feedback (to RQFS)
    • Dashboard →  ws://localhost:8004/ws/control (for live bias view)
"""

import asyncio, json, websockets
from datetime import datetime, timezone
from pathlib import Path

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
AQCI_PORT      = 8004
TCFK_STREAM    = "ws://localhost:8005/ws/fusion"
RQFS_FEEDBACK  = "ws://localhost:8006/ws/rqfs_feedback"

CONTROL_LOG = Path("data/control/aqci_log.jsonl")
CONTROL_LOG.parent.mkdir(parents=True, exist_ok=True)

CLIENTS = set()

# Adaptive bias parameters
bias_state = {"nu_bias": 0.0, "phi_bias": 0.0, "amp_bias": 0.0, "timestamp": None}

# Control gains
GAINS = {"k_nu": 0.015, "k_phi": 0.010, "k_amp": 0.005}

# ─────────────────────────────────────────────
# WebSocket Server Handler (3.12 compatible)
# ─────────────────────────────────────────────
async def aqci_ws(websocket):
    """Serve dashboards / monitors on :8004."""
    CLIENTS.add(websocket)
    print(f"🌐 AQCI client connected ({len(CLIENTS)} total)")
    try:
        await websocket.send(json.dumps({
            "type": "hello",
            "status": "connected",
            "bias": bias_state,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))
        async for _ in websocket:  # idle loop; client pings ignored
            pass
    except Exception as e:
        print(f"⚠️ AQCI client error: {e}")
    finally:
        CLIENTS.remove(websocket)
        print(f"🔻 AQCI client disconnected ({len(CLIENTS)} remaining)")

# ─────────────────────────────────────────────
# Adaptive Control Law
# ─────────────────────────────────────────────
def apply_control_law(delta_c: float):
    """Integrate Δ𝒞 into adaptive biases."""
    bias_state["nu_bias"]  += GAINS["k_nu"]  * delta_c
    bias_state["phi_bias"] += GAINS["k_phi"] * delta_c
    bias_state["amp_bias"]  = max(0.0, min(1.0,
                              bias_state["amp_bias"] + GAINS["k_amp"] * delta_c))
    bias_state["timestamp"] = datetime.now(timezone.utc).isoformat()
    return bias_state.copy()

async def handle_coherence_adjustment(delta: float):
    """React to new Δ𝒞 from TCFK."""
    new_bias = apply_control_law(delta)
    # Log
    with open(CONTROL_LOG, "a") as f:
        f.write(json.dumps({"delta": delta, "bias": new_bias}) + "\n")

    print(f"🧬 ΔC={delta:+.5f} → ν={new_bias['nu_bias']:+.5f} ϕ={new_bias['phi_bias']:+.5f} α={new_bias['amp_bias']:+.5f}")

    # Broadcast to dashboards
    if CLIENTS:
        msg = json.dumps({"type": "control_update", "delta": delta, "bias": new_bias})
        await asyncio.gather(*(c.send(msg) for c in list(CLIENTS)))

    # Forward to RQFS
    try:
        async with websockets.connect(RQFS_FEEDBACK) as ws:
            await ws.send(json.dumps({
                "type": "adaptive_bias_update",
                "bias": new_bias,
                "timestamp": new_bias["timestamp"],
            }))
    except Exception as e:
        print(f"⚠️ RQFS feedback unreachable: {e}")

# ─────────────────────────────────────────────
# Input Listener (from TCFK)
# ─────────────────────────────────────────────
async def listen_tcfk():
    """Subscribe to TCFK fusion stream and extract Δ𝒞."""
    print(f"🧠 Listening for TCFK coherence deltas on {TCFK_STREAM}")
    while True:
        try:
            async with websockets.connect(TCFK_STREAM) as ws:
                async for msg in ws:
                    try:
                        data = json.loads(msg)
                        if "delta_coherence" in data:
                            await handle_coherence_adjustment(float(data["delta_coherence"]))
                    except Exception:
                        continue
        except Exception as e:
            print(f"⚠️ TCFK stream error: {e}, retrying…")
            await asyncio.sleep(3)

# ─────────────────────────────────────────────
# Orchestration
# ─────────────────────────────────────────────
async def main():
    print("🧬 Starting Tessaris Adaptive Quantum Control Interface (AQCI)…")
    await websockets.serve(aqci_ws, "0.0.0.0", AQCI_PORT)
    print(f"🌐 AQCI running on ws://0.0.0.0:{AQCI_PORT}/ws/control")
    await listen_tcfk()  # single main loop

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🧩 AQCI stopped.")