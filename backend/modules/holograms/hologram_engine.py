# backend/modules/glyphos/hologram_engine.py

import json
from typing import List, Dict
from datetime import datetime
from backend.modules.hexcore.memory_engine import MEMORY
from backend.modules.codex.codex_metrics import CodexMetrics

class HologramEngine:
    def __init__(self, container_id: str):
        self.container_id = container_id
        self.memory = MEMORY.get(container_id)
        self.metrics = CodexMetrics(container_id)

    def generate_holographic_packet(self) -> Dict:
        """
        Construct a light-logic packet from container glyphs.
        Includes 4D positioning, entanglement, and type logic.
        """
        glyphs = self.memory.get_glyph_trace()
        packet = {
            "container_id": self.container_id,
            "generated": datetime.utcnow().isoformat() + "Z",
            "format": "GHX-1",
            "glyphs": []
        }

        for i, glyph in enumerate(glyphs):
            packet["glyphs"].append({
                "id": glyph.get("id", f"g{i}"),
                "glyph": glyph["glyph"],
                "label": glyph.get("label", ""),
                "position_4d": self._calculate_4d_position(i, len(glyphs)),
                "entangled": glyph.get("entangled", []),
                "light_code": self._encode_light_logic(glyph)
            })

        return packet

    def _calculate_4d_position(self, index: int, total: int) -> Dict:
        """
        Simple 4D spiral mapper: x, y, z + t based on order.
        """
        import math
        angle = 2 * math.pi * (index / max(total, 1))
        radius = 1.0 + (index * 0.1)
        return {
            "x": radius * math.cos(angle),
            "y": radius * math.sin(angle),
            "z": 0.1 * index,
            "t": index
        }

    def _encode_light_logic(self, glyph: Dict) -> str:
        """
        Encode glyph meaning into light color/symbolic code.
        """
        g = glyph["glyph"]
        mapping = {
            "⊕": "cyan-pulse",
            "↔": "purple-link",
            "⧖": "red-collapse",
            "🧠": "blue-think",
            "⬁": "green-mutate",
            "🛰️": "white-signal"
        }
        return mapping.get(g, "gray-static")

    def export_to_file(self, path: str) -> None:
        packet = self.generate_holographic_packet()
        with open(path, "w") as f:
            json.dump(packet, f, indent=2)