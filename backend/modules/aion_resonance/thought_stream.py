# ==========================================================
# 🧠 AION Thought Stream — WebSocket Live Feed
# ----------------------------------------------------------
# Streams cognitive reflections, LLM interpretations,
# Symatic encodings, and now conceptual updates
# in real-time via WebSocket broadcast.
# ==========================================================

import json
import asyncio
import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set
import datetime

# --- Phase 4 Conceptual Learning Arena Integration ---
from backend.modules.aion_concept.concept_learning_arena import (
    ConceptGraph,
    process_reflection_event,
)

# Initialize global concept graph instance
concept_graph = ConceptGraph()

# ──────────────────────────────────────────────────────────
# 📁 File Paths
# ──────────────────────────────────────────────────────────
MEMORY_PATH = "data/conversation_memory.json"
SYMATIC_PATH = "data/symatic_log.json"

router = APIRouter()
active_connections: Set[WebSocket] = set()

# ──────────────────────────────────────────────────────────
# 🔍 Utility: Load JSON safely
# ──────────────────────────────────────────────────────────
def load_json(path: str):
    try:
        if not os.path.exists(path):
            return []
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return []

# ──────────────────────────────────────────────────────────
# 🧩 Fetch last reflections + symatic encodings
# ──────────────────────────────────────────────────────────
async def fetch_recent_activity():
    memory = load_json(MEMORY_PATH)
    symatic_data = load_json(SYMATIC_PATH)
    symatic_log = symatic_data.get("log", []) if isinstance(symatic_data, dict) else []

    reflections = [
        {
            "type": e.get("type", "self_reflection"),
            "message": e.get("message", e.get("llm_output", "")),
            "tone": e.get("tone", "–"),
            "timestamp": e.get("timestamp", ""),
        }
        for e in memory[-10:]
        if e.get("type") in ["self_reflection", "llm_reflection"]
    ]

    equations = [
        {
            "type": "symatic",
            "message": f"{e.get('operator', '?')} {e.get('equation', '')}",
            "tone": "–",
            "timestamp": e.get("timestamp", ""),
        }
        for e in symatic_log[-10:]
    ]

    combined = reflections + equations
    combined.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return combined[:15]

# ──────────────────────────────────────────────────────────
# 📡 Broadcast helper
# ──────────────────────────────────────────────────────────
async def broadcast_event(event: dict):
    """Send JSON event to all connected clients."""
    if not active_connections:
        return
    dead = []
    for ws in active_connections.copy():
        try:
            await ws.send_json(event)
        except Exception:
            dead.append(ws)
    for ws in dead:
        active_connections.discard(ws)

# ──────────────────────────────────────────────────────────
# ==========================================================
# Conceptual Learning Hook (Phase 4)
# ==========================================================
async def handle_aion_event(event: dict):
    """
    Intercepts AION reflection/self_reflection events and sends them
    to the Concept Learning Arena for live semantic mapping.
    """
    if event.get("type") in ("aion_reflection", "self_reflection"):
        await process_reflection_event(event, concept_graph)

# ──────────────────────────────────────────────────────────
# 🌐 WebSocket endpoint (main)
# ──────────────────────────────────────────────────────────
@router.websocket("/api/aion/thought-stream")
async def thought_stream_socket(ws: WebSocket):
    """WebSocket: streams live AION cognitive + symatic events."""
    await ws.accept()
    active_connections.add(ws)
    print("📡 Client connected to AION Thought Stream.")

    # Initial push: recent reflections and symatic data
    events = await fetch_recent_activity()
    await ws.send_json({"type": "init", "events": events})
    last_snapshot = json.dumps(events)

    try:
        while True:
            await asyncio.sleep(5)
            new_events = await fetch_recent_activity()
            snapshot = json.dumps(new_events)
            if snapshot != last_snapshot:
                update_packet = {"type": "update", "events": new_events}
                await broadcast_event(update_packet)

                # Pass each reflection event to the Concept Arena
                for ev in new_events:
                    await handle_aion_event(ev)

                last_snapshot = snapshot
    except WebSocketDisconnect:
        active_connections.discard(ws)
        print("🔌 Client disconnected from AION Thought Stream.")
    except Exception as e:
        active_connections.discard(ws)
        print(f"⚠️ Thought Stream error: {e}")

# ──────────────────────────────────────────────────────────
# 🔗 Legacy WebSocket endpoint
# ──────────────────────────────────────────────────────────
@router.websocket("/ws/thought-stream")
async def legacy_thought_stream(ws: WebSocket):
    """Legacy alias for /api/aion/thought-stream"""
    await thought_stream_socket(ws)

# ✅ Export router for main.py
thought_stream_router = router