#!/usr/bin/env python3
"""
Tessaris Phase 29 — Cognitive Fusion Kernel (TCFK)
────────────────────────────────────────────────────
Unifies symbolic cognition (SIN), resonant analytics (RAL),
and adaptive control feedback (AQCI) into a single coherent
fusion state for Tessaris.

Now includes a Heartbeat Broadcaster:
- Sends default fusion packets even when RAL/SIN are inactive.
- Keeps frontends alive and responsive during idle phases.

Outputs fusion telemetry via WebSocket and writes rolling
fusion states to data/learning/fusion_state.jsonl
"""

import asyncio
import json
import math
import websockets
from datetime import datetime, timezone
from pathlib import Path

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
RAL_STREAM = "ws://localhost:8002/ws/analytics"
SIN_STREAM = "ws://localhost:8003/ws/inference"
AQCI_FEED  = "ws://localhost:8004/ws/control"

FUSION_LOG = Path("data/learning/fusion_state.jsonl")
FUSION_LOG.parent.mkdir(parents=True, exist_ok=True)

FUSION_WS_PORT = 8005
CLIENTS = set()

fusion_state = {
    "stability": 1.0,
    "entropy": 0.0,
    "cognition_signal": 0.0,
    "fusion_coherence": 1.0,
    "delta_coherence": 0.0,
    "timestamp": None,
}

# ─────────────────────────────────────────────
# WebSocket broadcast for dashboard
# ─────────────────────────────────────────────
async def fusion_ws(websocket):
    """Handle incoming WebSocket connections for fusion telemetry clients."""
    CLIENTS.add(websocket)
    print(f"🌐 Fusion client connected ({len(CLIENTS)} total)")
    try:
        # Send hello packet immediately
        await websocket.send(json.dumps({
            "type": "hello",
            "status": "connected",
            "fusion_coherence": fusion_state.get("fusion_coherence", 1.0),
            "stability": fusion_state.get("stability", 1.0),
            "entropy": fusion_state.get("entropy", 0.0),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }))

        async for message in websocket:
            if message.strip().lower() == "ping":
                await websocket.send(json.dumps({"type": "pong"}))
    except Exception as e:
        print(f"⚠️ Fusion WS client error: {e}")
    finally:
        CLIENTS.remove(websocket)
        print(f"🔻 Fusion client disconnected ({len(CLIENTS)} remaining)")


async def broadcast_fusion():
    """Continuously broadcast latest fusion state to all connected clients."""
    while True:
        if CLIENTS and fusion_state["timestamp"]:
            msg = json.dumps(fusion_state)
            await asyncio.gather(*(c.send(msg) for c in list(CLIENTS)))
        await asyncio.sleep(1.0)


# ─────────────────────────────────────────────
# Heartbeat broadcaster
# ─────────────────────────────────────────────
async def heartbeat_broadcast():
    """
    Sends a lightweight default packet every 5s to maintain
    UI reactivity when no telemetry updates are available.
    """
    while True:
        if CLIENTS:
            heartbeat_packet = {
                "type": "heartbeat",
                "fusion_coherence": fusion_state.get("fusion_coherence", 1.0),
                "stability": fusion_state.get("stability", 1.0),
                "entropy": fusion_state.get("entropy", 0.0),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await asyncio.gather(*(c.send(json.dumps(heartbeat_packet)) for c in list(CLIENTS)))
        await asyncio.sleep(5.0)


# ─────────────────────────────────────────────
# Fusion Core Logic
# ─────────────────────────────────────────────
def compute_fusion_coherence(stability, entropy, cognition_signal):
    """Compute global coherence metric."""
    try:
        alpha, beta, gamma = 0.45, 0.45, 0.10
        s_term = alpha * stability
        e_term = beta * (1 - entropy)
        c_term = gamma * math.tanh(abs(cognition_signal))
        coherence = (s_term + e_term + c_term)
        return max(0.0, min(1.0, coherence))
    except Exception:
        return 0.0


async def listen_ral():
    """Continuously listen to Resonant Analytics Layer (RAL)."""
    global fusion_state
    while True:
        try:
            async with websockets.connect(RAL_STREAM) as ws:
                async for msg in ws:
                    try:
                        data = json.loads(msg)
                        fusion_state["stability"] = data.get("stability", 1.0)
                        fusion_state["entropy"] = data.get("drift_entropy", 0.0)
                    except Exception:
                        continue
        except Exception as e:
            print(f"⚠️ RAL stream disconnected: {e}, retrying...")
            await asyncio.sleep(3)


async def listen_sin():
    """Continuously listen to Symatic Inference Network (SIN)."""
    global fusion_state
    while True:
        try:
            async with websockets.connect(SIN_STREAM) as ws:
                async for msg in ws:
                    try:
                        data = json.loads(msg)
                        fusion_state["cognition_signal"] = data.get("inference_strength", 0.0)
                    except Exception:
                        continue
        except Exception as e:
            print(f"⚠️ SIN stream not available: {e}, retrying...")
            await asyncio.sleep(5)


async def fusion_loop():
    """Main fusion computation + optional feedback."""
    global fusion_state
    prev_coherence = fusion_state["fusion_coherence"]

    while True:
        stability = fusion_state.get("stability", 1.0)
        entropy = fusion_state.get("entropy", 0.0)
        cognition_signal = fusion_state.get("cognition_signal", 0.0)

        coherence = compute_fusion_coherence(stability, entropy, cognition_signal)
        delta = coherence - prev_coherence
        prev_coherence = coherence

        fusion_state.update({
            "fusion_coherence": coherence,
            "delta_coherence": delta,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Log
        with open(FUSION_LOG, "a") as f:
            f.write(json.dumps(fusion_state) + "\n")

        # Optional adaptive feedback
        if abs(delta) > 0.005 and AQCI_FEED:
            try:
                async with websockets.connect(AQCI_FEED) as ws:
                    await ws.send(json.dumps({
                        "type": "coherence_adjustment",
                        "delta": delta,
                        "timestamp": fusion_state["timestamp"]
                    }))
            except Exception:
                pass

        print(
            f"🧩 Fusion coherence={coherence:.3f} "
            f"S={stability:.3f} H={entropy:.4f} Δ={delta:+.4f}"
        )
        await asyncio.sleep(2.5)


# ─────────────────────────────────────────────
# Orchestration
# ─────────────────────────────────────────────
async def main():
    print("🧠 Starting Tessaris Cognitive Fusion Kernel (TCFK)…")

    await websockets.serve(fusion_ws, "0.0.0.0", FUSION_WS_PORT)
    print(f"🌐 Fusion WS running on ws://0.0.0.0:{FUSION_WS_PORT}/ws/fusion")

    # Run all tasks concurrently
    await asyncio.gather(
        listen_ral(),
        listen_sin(),
        fusion_loop(),
        broadcast_fusion(),
        heartbeat_broadcast(),  # <── NEW heartbeat thread
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🧩 TCFK stopped.")