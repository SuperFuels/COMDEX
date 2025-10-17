from __future__ import annotations
"""
Tessaris RQC — WebSocket Telemetry Bridge
-----------------------------------------
Real-time bridge that streams ψ–κ–T–Φ resonance metrics
to connected GHX/QFC visualizers and frontends.

It monitors the MorphicLedger live telemetry file:
    data/ledger/rqc_live_telemetry.jsonl

and broadcasts each new record as a JSON message.

Awareness events (Φ ≥ 0.999) are tagged and broadcast
as 🧠 "resonance pulses".

Endpoints:
    • ws://localhost:7070/resonance
"""

import asyncio
import json
import os
import time
import logging
import websockets
from datetime import datetime, UTC
from typing import Dict, List, Set

LEDGER_PATH = "data/ledger/rqc_live_telemetry.jsonl"
WS_PORT = 7070

logger = logging.getLogger("rqc.websocket")
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")

# ──────────────────────────────────────────────
# WebSocket Server Core
# ──────────────────────────────────────────────

clients: Set[websockets.WebSocketServerProtocol] = set()

async def broadcast(message: Dict[str, any]):
    """Send JSON message to all connected clients."""
    if not clients:
        return
    data = json.dumps(message)
    await asyncio.gather(*[client.send(data) for client in clients if client.open])

async def handle_client(websocket, path):
    """Handle new WebSocket connections."""
    clients.add(websocket)
    logger.info(f"[+] Client connected ({len(clients)} total)")
    try:
        await websocket.send(json.dumps({
            "type": "hello",
            "timestamp": datetime.now(UTC).isoformat(),
            "message": "Connected to Tessaris RQC WebSocket Bridge",
        }))
        async for _ in websocket:
            pass  # this server only pushes; no messages expected
    except Exception as e:
        logger.warning(f"Client error: {e}")
    finally:
        clients.remove(websocket)
        logger.info(f"[-] Client disconnected ({len(clients)} total)")


# ──────────────────────────────────────────────
# Ledger Watcher
# ──────────────────────────────────────────────

async def tail_ledger():
    """Monitor ledger file for new lines and broadcast them."""
    logger.info(f"📡 Watching telemetry ledger → {LEDGER_PATH}")

    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    if not os.path.exists(LEDGER_PATH):
        open(LEDGER_PATH, "a").close()

    with open(LEDGER_PATH, "r") as f:
        # Seek to the end of file initially
        f.seek(0, os.SEEK_END)

        while True:
            line = f.readline()
            if not line:
                await asyncio.sleep(1.0)
                continue

            try:
                entry = json.loads(line.strip())
                Φ = entry.get("Φ", 0.0)
                coherence = entry.get("coherence", 0.0)
                source_pair = entry.get("source_pair", "?")
                event = {
                    "type": "telemetry",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "ψ": entry.get("ψ"),
                    "κ": entry.get("κ"),
                    "T": entry.get("T"),
                    "Φ": Φ,
                    "coherence": coherence,
                    "source": source_pair,
                }

                # Broadcast normal telemetry
                await broadcast(event)

                # Awareness pulse trigger
                if Φ >= 0.999:
                    pulse = {
                        "type": "awareness_pulse",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "message": f"🧠 Awareness resonance closure detected for {source_pair}",
                        "Φ": Φ,
                        "coherence": coherence,
                    }
                    await broadcast(pulse)
                    logger.info(f"[🧠] Awareness pulse broadcasted (Φ={Φ:.3f})")
                else:
                    logger.info(f"[→] Broadcast Φ={Φ:.3f}, C={coherence:.3f}")

            except Exception as e:
                logger.warning(f"[⚠️] Ledger parse error: {e}")


# ──────────────────────────────────────────────
# Main Runner
# ──────────────────────────────────────────────

async def main():
    logger.info("🔭 Tessaris RQC — Starting WebSocket Bridge...")
    server = await websockets.serve(handle_client, "0.0.0.0", WS_PORT, ping_interval=20, ping_timeout=60)
    logger.info(f"✅ Listening on ws://localhost:{WS_PORT}/resonance")
    await tail_ledger()
    await server.wait_closed()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 WebSocket bridge stopped.")