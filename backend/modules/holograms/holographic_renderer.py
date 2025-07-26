import os
import uuid
import math
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from backend.modules.hologram.ghx_encoder import glyph_color_map, glyph_intensity_map
from backend.modules.symbolic_entangler import get_entangled_links
from backend.modules.codex.codex_trace import trace_glyph_execution_path
from backend.modules.codex.codex_metrics import calculate_glyph_cost

logger = logging.getLogger(__name__)

class HolographicRenderer:
    def __init__(self, ghx_packet: Dict[str, Any]):
        self.ghx = ghx_packet
        self.rendered_projection: List[Dict] = []
        self.links: List[Dict] = []

    def render_glyph_field(self) -> List[Dict]:
        """
        Project each glyph into a symbolic 4D light field.
        """
        projection = []
        glyphs = self.ghx.get("glyphs") or self.ghx.get("holograms", [])
        for glyph in glyphs:
            gid = glyph.get("id")
            symbol = glyph.get("glyph") or glyph.get("symbol")
            label = glyph.get("label", "")
            timestamp = glyph.get("timestamp", datetime.utcnow().isoformat())

            position = self._calc_4d_position(glyph)
            entangled = glyph.get("entangled", []) or get_entangled_links(gid)
            replay = glyph.get("replay", []) or trace_glyph_execution_path(gid)
            cost = glyph.get("cost", 0.0) or calculate_glyph_cost(symbol)

            light_packet = {
                "glyph_id": gid,
                "symbol": symbol,
                "label": label,
                "light_intensity": self._calc_light_intensity(symbol),
                "color": glyph_color_map(symbol),
                "animation": "pulse",
                "position": position,
                "entangled": entangled,
                "trigger_state": "idle",
                "collapse_trace": symbol in ("⧖", "⬁"),
                "replay": replay,
                "cost": cost,
                "timestamp": timestamp
            }
            projection.append(light_packet)

            for eid in entangled:
                self.links.append({
                    "source": gid,
                    "target": eid,
                    "type": "entanglement",
                    "color": "#aa00ff",
                    "animated": True
                })

        self.rendered_projection = projection
        return projection

    def get_active_glyphs(self) -> List[str]:
        """
        Return currently projected glyph symbols for AvatarThoughtAura overlay.
        """
        return [glyph["symbol"] for glyph in self.rendered_projection]

    def trigger_projection(self, glyph_id: str, method: str = "gaze") -> Optional[Dict]:
        """
        Simulate an observer triggering a glyph by proximity, gaze, etc.
        """
        for glyph in self.rendered_projection:
            if glyph["glyph_id"] == glyph_id:
                glyph["trigger_state"] = f"triggered_by_{method}"
                glyph["activated_at"] = datetime.utcnow().isoformat()
                return glyph
        return None

    def _calc_light_intensity(self, symbol: str) -> float:
        """
        Determine holographic light strength based on glyph type.
        """
        return glyph_intensity_map(symbol)

    def _calc_4d_position(self, glyph: Dict) -> Dict:
        """
        Encode symbolic spatial position for glyphs.
        """
        gid = glyph.get("id", "")
        seed = uuid.uuid5(uuid.NAMESPACE_DNS, gid)
        return {
            "x": (seed.int % 50) - 25,
            "y": (seed.int % 70) - 35,
            "z": (seed.int % 90) - 45,
            "t": glyph.get("timestamp", "2025-07-25T00:00:00Z")
        }

    def export_projection(self) -> Dict:
        """
        Return the rendered light field as a symbolic structure.
        """
        return {
            "rendered_at": datetime.utcnow().isoformat(),
            "projection_id": str(uuid.uuid4()),
            "container_id": self.ghx.get("container_id"),
            "physics": self.ghx.get("physics", "symbolic-quantum"),
            "dimensions": self.ghx.get("dimensions", 4),
            "nodes": self.rendered_projection,
            "links": self.links,
            "metadata": {
                "version": self.ghx.get("ghx_version", "1.0"),
                "replay_enabled": self.ghx.get("replay_enabled", False)
            }
        }

    def export_to_json(self, path: str):
        """
        Write the rendered holographic graph to disk as JSON.
        """
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.export_projection(), f, indent=2)