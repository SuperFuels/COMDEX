"""
🔵 QFC Resonance Overlay - SRK-19.3 Fusion Update
Bridges GHX resonance frames -> QFC holographic overlay payloads
and records each broadcasted frame into GWV visual logs.

Now integrates:
 * Live CFE feedback telemetry (collapse_rate, decoherence_rate, stability)
 * Adaptive hue modulation based on cognitive coherence feedback
 * GHX + CFE fusion stream for CodexHUD live overlays

Features:
 * Translates GHX nodes/edges into QFC packets
 * Maps coherence -> RGB hue, stability -> global brightness
 * Supports holographic_projection() for 3-D visualization layers
 * Streams overlays to QFC WebSocket via broadcast_qfc_update()
 * Archives resonance frames using GWVWriter for playback analysis
"""

import time
from typing import Dict, Any, Optional

from backend.cfe.cfe_feedback_loop import CFEFeedbackLoop
from backend.modules.visualization.ghx_visual_bridge import GHXVisualBridge
from backend.modules.visualization.broadcast_qfc_update import broadcast_qfc_update
from backend.modules.glyphwave.gwv_writer import SnapshotRingBuffer


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp a float into the inclusive range [low, high]."""
    return max(low, min(high, value))


def _hsv_to_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    """Convert HSV (0-1) -> RGB tuple (0-255)."""
    h = h % 1.0
    s = _clamp(s, 0.0, 1.0)
    v = _clamp(v, 0.0, 1.0)

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


def _extract_hue(color: object, default_hue: float = 270.0 / 360.0) -> float:
    """
    Accept legacy HSL strings and newer dict-based color payloads.

    Supported inputs:
      * "hsl(270,80%,80%)"
      * {"h": 270}
      * {"hue": 270}
      * {"hsl": {"h": 270}}
      * {"color": {"hue": 270}}
      * numeric hue strings / ints / floats

    Returns:
      normalized hue in [0, 1)
    """
    if color is None:
        return default_hue

    if isinstance(color, (int, float)):
        return (float(color) / 360.0) % 1.0

    if isinstance(color, dict):
        for key in ("h", "hue"):
            value = color.get(key)
            if isinstance(value, (int, float)):
                return (float(value) / 360.0) % 1.0

        for nested_key in ("hsl", "color", "fill", "stroke"):
            nested = color.get(nested_key)
            if isinstance(nested, dict):
                for key in ("h", "hue"):
                    value = nested.get(key)
                    if isinstance(value, (int, float)):
                        return (float(value) / 360.0) % 1.0
            elif isinstance(nested, str):
                parsed = _extract_hue(nested, default_hue=default_hue)
                if parsed != default_hue or nested.strip().startswith("hsl("):
                    return parsed

        return default_hue

    if isinstance(color, str):
        text = color.strip()

        if text.startswith("hsl(") and ")" in text:
            try:
                hue_raw = text.split("(", 1)[1].split(",", 1)[0].strip()
                return (float(hue_raw) / 360.0) % 1.0
            except (ValueError, IndexError):
                return default_hue

        try:
            return (float(text) / 360.0) % 1.0
        except ValueError:
            return default_hue

    return default_hue


class QFCResonanceOverlay:
    """Builds, streams, and archives QFC overlay packets from GHX frames."""

    def __init__(self, ghx_bridge: GHXVisualBridge, feedback: Optional[CFEFeedbackLoop] = None):
        self.bridge = ghx_bridge
        self.feedback = feedback
        self._brightness_bias = 0.85
        self._gwv_buffer = SnapshotRingBuffer(maxlen=90)

    async def build_overlay(self) -> Dict[str, Any]:
        """Translate latest GHX frame into QFC overlay format (with CFE telemetry)."""
        frame = await self.bridge.build_frame()

        frame_stability = float(frame.get("stability", 1.0))
        brightness = _clamp(max(0.2, frame_stability) * self._brightness_bias, 0.0, 1.0)

        feedback_data: Dict[str, Any] = {}
        if self.feedback and getattr(self.feedback, "last_feedback", None):
            feedback_data = dict(self.feedback.last_feedback)

        hue_bias = 0.0
        if "symbolic_temperature" in feedback_data:
            try:
                hue_bias = float(feedback_data["symbolic_temperature"]) * 0.1
            except (TypeError, ValueError):
                hue_bias = 0.0

        nodes = []
        for node in frame.get("nodes", []):
            base_hue = _extract_hue(node.get("color", "hsl(270,80%,80%)"))
            hue = (base_hue + hue_bias) % 1.0
            r, g, b = _hsv_to_rgb(hue, 0.8, brightness)
            nodes.append(
                {
                    "id": node["id"],
                    "rgb": (r, g, b),
                    "alpha": brightness,
                }
            )

        edges = []
        for edge in frame.get("edges", []):
            coherence = float(edge.get("coherence", 1.0))
            hue = (0.75 - (coherence * 0.25) + hue_bias) % 1.0
            r, g, b = _hsv_to_rgb(hue, 0.8, brightness)
            edges.append(
                {
                    "source": edge["source"],
                    "target": edge["target"],
                    "rgb": (r, g, b),
                    "phi": edge.get("phi"),
                    "coherence": coherence,
                }
            )

        overlay = {
            "type": "qfc_resonance_overlay",
            "timestamp": time.time(),
            "stability": frame_stability,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
            "feedback": feedback_data,
        }

        self._gwv_buffer.add_snapshot(
            collapse_rate=1.0 - frame_stability,
            decoherence_rate=(1.0 - brightness),
            frame_data=overlay,
        )
        return overlay

    async def holographic_projection(self) -> Dict[str, Any]:
        """Compute holographic 3-D projection frame (brightness-weighted)."""
        overlay = await self.build_overlay()
        nodes = overlay["nodes"]

        for node in nodes:
            node["z"] = (1.0 - float(node["alpha"])) * 2.0

        overlay["projection"] = {
            "mode": "holographic",
            "depth_field": [node["z"] for node in nodes],
        }
        return overlay

    async def broadcast_overlay(self, container_id: str) -> Dict[str, Any]:
        """Stream overlay to QFC via websocket and archive to GWV."""
        overlay = await self.build_overlay()
        try:
            await broadcast_qfc_update(container_id, overlay)
            self._gwv_buffer.export_to_gwv(container_id=container_id)
            return {"status": "broadcast", "nodes": overlay["node_count"]}
        except Exception as e:
            return {"status": "failed", "error": str(e)}