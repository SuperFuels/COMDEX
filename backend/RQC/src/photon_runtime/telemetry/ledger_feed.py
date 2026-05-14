# backend/RQC/src/photon_runtime/telemetry/ledger_feed.py
"""
Tessaris RQC - Morphic Ledger Feed
────────────────────────────────────────────────────────
Serves real-time Φ-ψ-κ-T telemetry entries from the MorphicLedger
(JSONL ledger -> Web API -> CodexTrace Visualizer).

Endpoints:
    GET /telemetry/ledger/latest   -> last N entries (JSON)
    GET /telemetry/ledger/stream   -> live Server-Sent Events (SSE)
"""

import os
import json
import asyncio
from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from watchfiles import awatch

LEDGER_PATH = "data/ledger/rqc_live_telemetry.jsonl"
router = APIRouter(prefix="/telemetry/ledger", tags=["telemetry"])

# ────────────────────────────────
# helpers
# ────────────────────────────────
def _read_latest_entries(limit: int = 50):
    """Return most recent N records from the ledger."""
    if not os.path.exists(LEDGER_PATH):
        return []
    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()[-limit:]
    return [json.loads(line) for line in lines if line.strip()]


# ────────────────────────────────
# routes
# ────────────────────────────────
@router.get("/latest")
async def get_latest(n: int = 50):
    """Return last N entries as JSON."""
    entries = _read_latest_entries(n)
    return JSONResponse(content={"count": len(entries), "entries": entries})


@router.get("/stream")
async def stream_ledger():
    """Continuously stream new ledger records as SSE (events for frontend)."""

    async def event_generator():
        last_size = os.path.getsize(LEDGER_PATH) if os.path.exists(LEDGER_PATH) else 0
        while True:
            async for _ in awatch(os.path.dirname(LEDGER_PATH)):
                if not os.path.exists(LEDGER_PATH):
                    continue
                size = os.path.getsize(LEDGER_PATH)
                if size > last_size:
                    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
                        f.seek(last_size)
                        new_data = f.read()
                        for line in new_data.strip().splitlines():
                            try:
                                evt = json.loads(line)
                                yield f"data: {json.dumps(evt)}\n\n"
                            except json.JSONDecodeError:
                                continue
                    last_size = size
            await asyncio.sleep(1.0)

    return Response(event_generator(), media_type="text/event-stream")