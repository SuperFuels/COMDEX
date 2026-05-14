"""
📄 brain_map_streamer.py

🧠 Knowledge Brain Map Streamer for AION & IGI  
Streams live KG node updates, QGlyph collapse ripples, and entangled confidence feedback to the frontend.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌌 Brain Map Streamer - Design Rubric
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Live WebSocket Streaming of KG Node & Link Events
✅ Confidence & Entropy Weight Broadcasting (CodexMetrics)
✅ ⚛ QGlyph Collapse Ripple Propagation (Entangled Zones)
✅ ↔ Entangled Glyph Zone Update Integration
✅ Success vs Failure Gradient Feedback Injection
✅ Ripple Animation Event for KnowledgeBrainMap.tsx Glow
✅ Scalable for Multi-Agent Knowledge Graph Fusion
✅ Optimized for KnowledgeBrainMap.tsx Reactive Rendering
"""

import json
import asyncio
from typing import Dict, Any, List
from fastapi import WebSocket
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer 
from backend.modules.glyphos.symbolic_entangler import get_entangled_for, get_entangled_targets

class BrainMapStreamer:
    def __init__(self):
        self.clients: List[WebSocket] = []
        self.kg_writer = get_kg_writer()
        self.metrics = CodexMetrics()

    # ──────────────────────────────
    # WebSocket Connection Management
    # ──────────────────────────────
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.clients.append(websocket)
        print("🔌 BrainMapStreamer: Client connected.")
        # Auto-send KG snapshot to new clients
        await self.stream_full_kg_snapshot()

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.clients:
            self.clients.remove(websocket)
            print("🔌 BrainMapStreamer: Client disconnected.")

    async def broadcast(self, event: Dict[str, Any]):
        """Broadcast a JSON event to all connected clients."""
        msg = json.dumps(event)
        for ws in list(self.clients):  # prevent concurrent mutation errors
            try:
                await ws.send_text(msg)
            except Exception as e:
                print(f"⚠️ BrainMapStreamer broadcast failed: {e}")

    # ──────────────────────────────
    # Node Update Streaming
    # ──────────────────────────────
    async def stream_node_update(self, glyph_id: str, status: str = "neutral"):
        """Send a live node update (confidence, entropy, status) to BrainMap."""
        node_data = self.kg_writer.get_node_metadata(glyph_id)
        confidence = self.metrics.get_confidence(glyph_id) or 0.5
        entropy = node_data.get("entropy", 0.0)

        event = {
            "type": "node_update",
            "node": {
                "id": glyph_id,
                "label": node_data.get("label", glyph_id),
                "confidence": confidence,
                "entropy": entropy,
                "status": status,
            },
        }
        await self.broadcast(event)

    # ──────────────────────────────
    # Link Update Streaming (↔ Entangled Nodes)
    # ──────────────────────────────
    async def stream_link_update(self, source_id: str, target_id: str):
        """Send a new entangled link (↔) update to the BrainMap UI."""
        event = {
            "type": "link_update",
            "link": {"source": source_id, "target": target_id},
        }
        await self.broadcast(event)

    # ──────────────────────────────
    # Gradient Feedback Streaming
    # ──────────────────────────────
    async def stream_gradient_feedback(self, glyph_id: str, confidence_delta: float, reason: str):
        """
        Broadcast gradient weight adjustments (confidence re-weighting) in real-time.
        This ties directly into SymbolicGradientEngine feedback.
        """
        event = {
            "type": "gradient_feedback",
            "glyph_id": glyph_id,
            "delta": confidence_delta,
            "reason": reason,
            "tags": ["⮌", "↔", "🧠"]
        }
        await self.broadcast(event)
        await self.stream_node_update(glyph_id)  # Refresh node glow with updated confidence

    # ──────────────────────────────
    # Collapse Ripple Streaming (⚛ Ripple Glow)
    # ──────────────────────────────
    async def stream_collapse_ripple(self, collapse_event: Dict):
        """
        Send collapse ripple glow event through entangled glyph zones.
        Each entangled glyph will emit a 'ripple' animation in KnowledgeBrainMap.tsx.
        """
        qglyph_id = collapse_event.get("selected", {}).get("qbit_id")
        entangled = get_entangled_for(qglyph_id)

        ripple_payload = {
            "type": "collapse_ripple",
            "origin": qglyph_id,
            "entangled_nodes": entangled,
            "bias": collapse_event.get("observer_bias"),
            "timestamp": collapse_event.get("timestamp"),
        }
        await self.broadcast(ripple_payload)

        # Update entangled nodes with collapse glow
        for glyph in entangled:
            await self.stream_node_update(glyph, status="collapse")

    # ──────────────────────────────
    # Full KG Snapshot Sync
    # ──────────────────────────────
    async def stream_full_kg_snapshot(self):
        """Pushes the entire current KG state to a newly connected client."""
        snapshot = self.kg_writer.export_full_graph()
        event = {
            "type": "kg_snapshot",
            "nodes": snapshot["nodes"],
            "links": snapshot["links"],
        }
        await self.broadcast(event)