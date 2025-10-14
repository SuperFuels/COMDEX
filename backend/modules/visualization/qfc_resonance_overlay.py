"""
🔵 QFC Resonance Overlay — SRK-19.2 Update
Bridges GHX resonance frames → QFC holographic overlay payloads
and records each broadcasted frame into GWV visual logs.

Features:
 • Translates GHX nodes/edges into QFC packets
 • Maps coherence → RGB hue, stability → global brightness
 • Supports holographic_projection() for 3-D visualization layers
 • Streams overlays to QFC WebSocket via broadcast_qfc_update()
 • Archives resonance frames using GWVWriter for playback analysis
"""

import math
import asyncio
import time
from typing import Dict, Any, List

from backend.modules.visualization.ghx_visual_bridge import GHXVisualBridge
from backend.modules.visualization.broadcast_qfc_update import broadcast_qfc_update
from backend.modules.glyphwave.gwv_writer import SnapshotRingBuffer  # ✅ new

def _hsv_to_rgb(h, s, v):
    """Convert HSV (0-1) → RGB tuple (0-255)."""
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    i %= 6
    r, g, b = [
        (v, t, p),
        (q, v, p),
        (p, v, t),
        (p, q, v),
        (t, p, v),
        (v, p, q),
    ][i]
    return int(r * 255), int(g * 255), int(b * 255)


class QFCResonanceOverlay:
    """Builds, streams, and archives QFC overlay packets from GHX frames."""

    def __init__(self, ghx_bridge: GHXVisualBridge):
        self.bridge = ghx_bridge
        self._brightness_bias = 0.85
        # ✅ initialize a local visual log ring buffer (SRK-19)
        self._gwv_buffer = SnapshotRingBuffer(maxlen=90)

    async def build_overlay(self) -> Dict[str, Any]:
        """Translate latest GHX frame into QFC overlay format."""
        frame = await self.bridge.build_frame()
        brightness = max(0.2, frame["stability"]) * self._brightness_bias

        nodes = []
        for node in frame["nodes"]:
            color = node.get("color", "hsl(270,80%,80%)")
            hue = float(color.split("(")[1].split(",")[0]) / 360.0
            r, g, b = _hsv_to_rgb(hue, 0.8, brightness)
            nodes.append({
                "id": node["id"],
                "rgb": (r, g, b),
                "alpha": brightness,
            })

        edges = []
        for edge in frame["edges"]:
            coherence = edge.get("coherence", 1.0)
            hue = 0.75 - (coherence * 0.25)
            r, g, b = _hsv_to_rgb(hue, 0.8, brightness)
            edges.append({
                "source": edge["source"],
                "target": edge["target"],
                "rgb": (r, g, b),
                "phi": edge.get("phi"),
                "coherence": coherence,
            })

        overlay = {
            "type": "qfc_resonance_overlay",
            "timestamp": time.time(),
            "stability": frame["stability"],
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
        }

        # ✅ add to visual ring buffer for persistence
        self._gwv_buffer.add_snapshot(
            collapse_rate=1.0 - frame["stability"],
            decoherence_rate=(1.0 - brightness),
        )
        return overlay

    async def holographic_projection(self):
        """Compute holographic 3-D projection frame (brightness-weighted)."""
        overlay = await self.build_overlay()
        nodes = overlay["nodes"]
        for n in nodes:
            n["z"] = (1.0 - n["alpha"]) * 2.0
        overlay["projection"] = {
            "mode": "holographic",
            "depth_field": [n["z"] for n in nodes],
        }
        return overlay

    async def broadcast_overlay(self, container_id: str):
        """Stream overlay to QFC via websocket and archive to GWV."""
        overlay = await self.build_overlay()
        try:
            await broadcast_qfc_update(container_id, overlay)
            # ✅ persist the buffer snapshot for analysis every broadcast cycle
            self._gwv_buffer.export_to_gwv(container_id=container_id)
            return {"status": "broadcast", "nodes": overlay["node_count"]}
        except Exception as e:
            return {"status": "failed", "error": str(e)}