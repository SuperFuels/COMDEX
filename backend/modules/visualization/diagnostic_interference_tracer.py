"""
🧩 Diagnostic Interference Tracer - SRK-20 Task 1
Visual diagnostic engine for constructive/destructive interference.

Purpose:
 * Analyze phase relationships across GHX nodes and edges
 * Detect coherence loss zones via CFE feedback + stability metrics
 * Generate diagnostic overlays for CodexHUD / QFC render
 * Optional persistence to GWV for playback inspection
"""

import math
import time
from typing import Dict, Any, List, Optional

from backend.modules.visualization.ghx_visual_bridge import GHXVisualBridge
from backend.modules.glyphwave.gwv_writer import SnapshotRingBuffer
from backend.modules.visualization.broadcast_qfc_update import broadcast_qfc_update
from backend.cfe.cfe_feedback_loop import CFEFeedbackLoop

# ===============================================================
# Utility - Schema-compliant color expansion
# ===============================================================
def _expand_node_colors(nodes):
    """Ensure nodes have schema-required rgb + alpha fields."""
    expanded = []
    for n in nodes:
        color = n.get("color", "hsl(200,80%,60%)")
        try:
            hue = int(color.split("(")[1].split(",")[0]) if "hsl" in color else 200
        except Exception:
            hue = 200
        rgb = [
            round((abs(math.sin(hue / 60)) * 255)),
            round((abs(math.sin((hue + 120) / 60)) * 255)),
            round((abs(math.sin((hue + 240) / 60)) * 255)),
        ]
        expanded.append({
            **n,
            "rgb": rgb,
            "alpha": 0.9,
        })
    return expanded


class DiagnosticInterferenceTracer:
    """Computes and streams interference diagnostics from GHX + CFE."""

    def __init__(
        self,
        ghx_bridge: GHXVisualBridge,
        feedback: Optional[CFEFeedbackLoop] = None,
    ):
        self.bridge = ghx_bridge
        self.feedback = feedback
        # Extended ring buffer for visual diagnostic logging
        self._ring_buffer = SnapshotRingBuffer(maxlen=120)

    # ===============================================================
    # Diagnostic Frame Builder
    # ===============================================================
    async def build_diagnostic_frame(self) -> Dict[str, Any]:
        """Generate interference diagnostic overlay frame."""
        frame = await self.bridge.build_frame()
        feedback_data = (
            self.feedback.last_feedback if self.feedback and self.feedback.last_feedback else {}
        )

        stability = frame.get("stability", 1.0)
        resonance_gain = feedback_data.get("resonance_gain", 1.0)

        zones: List[Dict[str, Any]] = []
        destructive, constructive = 0, 0

        for edge in frame.get("edges", []):
            phi = edge.get("phi", 0.0)
            coherence = edge.get("coherence", 1.0)
            interference_index = math.cos(phi * math.pi * 2) * coherence * resonance_gain

            if interference_index > 0.2:
                label = "constructive"
                constructive += 1
            elif interference_index < -0.2:
                label = "destructive"
                destructive += 1
            else:
                label = "neutral"

            zones.append({
                "source": edge.get("source"),
                "target": edge.get("target"),
                "phi": phi,
                "interference_index": round(interference_index, 3),
                "zone": label,
                "coherence": coherence,
            })

        avg_interference = (
            sum(z["interference_index"] for z in zones) / len(zones)
            if zones else 0.0
        )

        # ✅ Construct schema-valid inner frame
        inner_frame = {
            "schema_version": "1.1",
            "type": "diagnostic_interference_frame",
            "timestamp": time.time(),
            "stability": stability,
            "resonance_gain": resonance_gain,
            "constructive_count": constructive,
            "destructive_count": destructive,
            "avg_interference_index": round(avg_interference, 4),
            "interference_index": round(avg_interference, 4),
            "zones": zones,
            "nodes": frame.get("nodes", []),
            "edges": frame.get("edges", []),
        }

        # ✅ FIX - remove double wrapping when storing snapshot
        self._ring_buffer.add_snapshot(
            inner_frame,  # pass directly; inner_frame already schema-valid
            1.0 - stability,
            max(0.0, destructive / max(1, len(zones))),
        )

        # ✅ Ensure nodes have schema-required rgb + alpha fields
        inner_frame["nodes"] = _expand_node_colors(inner_frame.get("nodes", []))

        # ✅ Guarantee schema_version consistency inside buffered frames
        if hasattr(self._ring_buffer, "buffer") and self._ring_buffer.buffer:
            corrected_buffer = []
            for f in self._ring_buffer.buffer:
                if isinstance(f, dict):
                    # Wrap if missing "frame"
                    if "frame" not in f:
                        f = {"frame": f}
                    f["frame"].setdefault("schema_version", "1.1")

                    # Expand node colors in each stored frame
                    if "nodes" in f["frame"]:
                        f["frame"]["nodes"] = _expand_node_colors(f["frame"]["nodes"])

                    corrected_buffer.append(f)
            self._ring_buffer.buffer = corrected_buffer

        # ✅ Return top-level diagnostic frame
        return inner_frame
    # ===============================================================
    # Live Broadcast + Persistence
    # ===============================================================
    async def broadcast_diagnostics(self, container_id: str):
        """Emit live diagnostic overlay frame via QFC WebSocket and export to GWV."""
        frame = await self.build_diagnostic_frame()
        frame.setdefault("schema_version", "GWV-1.0")

        try:
            # ✅ Ensure color schema compliance for live broadcast
            if "nodes" in frame:
                frame["nodes"] = _expand_node_colors(frame["nodes"])

            # ✅ Send live diagnostic to Codex QFC overlay
            await broadcast_qfc_update(container_id, frame)

            # ✅ Ensure all buffered frames are schema-compliant
            if hasattr(self._ring_buffer, "frames") and self._ring_buffer.frames:
                corrected_frames = []
                for f in self._ring_buffer.frames:
                    if isinstance(f, dict):
                        if "frame" not in f:
                            f = {"frame": f}
                        inner = f["frame"]
                        inner.setdefault("schema_version", "GWV-1.0")
                        if "nodes" in inner:
                            inner["nodes"] = _expand_node_colors(inner["nodes"])
                        corrected_frames.append({"frame": inner})
                self._ring_buffer.frames = corrected_frames

            # ✅ Ensure container-level nodes are schema-valid before export
            if hasattr(self._ring_buffer, "export_to_gwv"):
                if "nodes" in frame:
                    frame["nodes"] = _expand_node_colors(frame["nodes"])
                    # attach at export-level for GWVWriter schema
                    self._ring_buffer.container_nodes = frame["nodes"]

            # ✅ Export wrapped, schema-valid frames to .gwv
            self._ring_buffer.export_to_gwv(container_id)

            return {
                "status": "broadcast",
                "zones": len(frame.get("zones", [])),
                "constructive": frame.get("constructive_count", 0),
                "destructive": frame.get("destructive_count", 0),
            }

        except Exception as e:
            print(f"[DiagnosticInterferenceTracer] Export or broadcast failed -> {e}")
            return {"status": "failed", "error": str(e)}