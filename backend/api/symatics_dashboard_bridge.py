#!/usr/bin/env python3
"""
Tessaris Phase 24 — Symatics Dashboard Bridge (SDB)

Bridges the live symbolic resonance stream (.glyph)
to FastAPI WebSocket clients for real-time visualization.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI(title="Tessaris Symatics Dashboard Bridge")

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
GLYPH_PATH = Path("data/symatics/symbolic_resonance_stream.glyph")
connected_clients = set()

# ------------------------------------------------------------
# Helper: broadcast to all active clients
# ------------------------------------------------------------
async def broadcast(message: dict):
    disconnected = set()
    for ws in connected_clients:
        try:
            await ws.send_json(message)
        except WebSocketDisconnect:
            disconnected.add(ws)
    connected_clients.difference_update(disconnected)

# ------------------------------------------------------------
# Background task: monitor glyph file for updates
# ------------------------------------------------------------
async def tail_glyph_stream():
    last_size = 0
    while True:
        try:
            if GLYPH_PATH.exists():
                new_size = GLYPH_PATH.stat().st_size
                if new_size > last_size:
                    with open(GLYPH_PATH, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    if lines:
                        entry = json.loads(lines[-1])
                        entry["t_sent"] = datetime.now(timezone.utc).isoformat()
                        await broadcast(entry)
                    last_size = new_size
        except Exception as e:
            print(f"⚠️ Glyph stream error: {e}")
        await asyncio.sleep(1.0)

# ------------------------------------------------------------
# WebSocket route
# ------------------------------------------------------------
@app.websocket("/ws/symatics")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    print("🧭 New Symatics client connected.")
    try:
        while True:
            # keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        print("🧭 Symatics client disconnected.")

# ------------------------------------------------------------
# Startup event: launch glyph watcher
# ------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(tail_glyph_stream())
    print("🪶 Symatics Dashboard Bridge active.")