"""
Tessaris RQC — CodexTrace WebSocket Relay
────────────────────────────────────────────
Bridges awareness and telemetry streams to frontend GHX widgets.

Sources:
  • data/ledger/rqc_live_telemetry.jsonl
  • data/analytics/awareness_summary.jsonl
  • MorphicLedger (Φ-awareness trend)

Broadcasts:
  • telemetry → ψ, κ, T, Φ, coherence
  • awareness → meta-awareness updates
  • phi_trend → rolling Φ trend + stability index
"""

import os
import json
import asyncio
import logging
import websockets
from websockets.server import serve
from datetime import datetime

logger = logging.getLogger("CodexTraceRelay")

LEDGER_PATH = "data/ledger/rqc_live_telemetry.jsonl"
AWARENESS_PATH = "data/analytics/awareness_summary.jsonl"

CONNECTED_CLIENTS = set()

# ────────────────────────────────
async def broadcast(message: dict):
    """Send message to all connected clients."""
    if not CONNECTED_CLIENTS:
        return
    msg_json = json.dumps(message)
    for ws in list(CONNECTED_CLIENTS):
        try:
            await ws.send(msg_json)
        except Exception:
            CONNECTED_CLIENTS.remove(ws)
    logger.info(f"📡 Broadcasted: {message.get('type')} Φ≈{message.get('Φ', message.get('mean_Φ', '—'))}")

# ────────────────────────────────
async def tail_file(path, kind):
    """Watch a file for new lines and broadcast structured updates."""
    last_size = os.path.getsize(path) if os.path.exists(path) else 0
    while True:
        if os.path.exists(path):
            size = os.path.getsize(path)
            if size > last_size:
                with open(path, "r", encoding="utf-8") as f:
                    f.seek(last_size)
                    new_data = f.read()
                    for line in new_data.strip().splitlines():
                        try:
                            evt = json.loads(line)
                            evt["type"] = kind
                            await broadcast(evt)
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to broadcast {kind} event: {e}")
                last_size = size
        await asyncio.sleep(1.0)

# ────────────────────────────────
async def broadcast_phi_trend(interval: float = 10.0):
    """Continuously broadcast Φ-awareness trend summary from MorphicLedger."""
    try:
        from backend.modules.holograms.morphic_ledger import morphic_ledger
    except Exception as e:
        logger.warning(f"[ΦTrend] Unable to import MorphicLedger: {e}")
        return

    while True:
        try:
            trend = morphic_ledger.get_phi_trend()
            if trend.get("count", 0) > 0:
                trend["type"] = "phi_trend"
                trend["timestamp"] = datetime.utcnow().isoformat()
                await broadcast(trend)
        except Exception as e:
            logger.warning(f"[ΦTrend] Broadcast failed: {e}")
        await asyncio.sleep(interval)

# ────────────────────────────────
async def handle_connection(websocket):
    CONNECTED_CLIENTS.add(websocket)
    addr = websocket.remote_address
    logger.info(f"🔌 Client connected: {addr}")
    try:
        await websocket.wait_closed()
    finally:
        CONNECTED_CLIENTS.remove(websocket)
        logger.info(f"🔌 Client disconnected: {addr}")

# ────────────────────────────────
async def main():
    logger.info("🚀 Tessaris RQC — CodexTrace WebSocket Relay starting...")
    os.makedirs("data/analytics", exist_ok=True)
    os.makedirs("data/ledger", exist_ok=True)

    async with serve(handle_connection, "0.0.0.0", 7071):
        logger.info("✅ Listening on ws://localhost:7071/codextrace")
        await asyncio.gather(
            tail_file(LEDGER_PATH, "telemetry"),
            tail_file(AWARENESS_PATH, "awareness"),
            broadcast_phi_trend(10.0),
        )

# ────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
    asyncio.run(main())