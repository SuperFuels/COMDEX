# File: backend/modules/sqi/entangler_engine.py

from typing import Dict, List, Tuple

class EntanglerEngine:
    """
    Symbolic Entangler Engine for SQI
    Links two or more Q-Glyphs together in a non-local relationship
    """

    def __init__(self):
        self.entangled_pairs: List[Tuple[str, str]] = []
        self.entanglement_map: Dict[str, List[str]] = {}

    def entangle(self, glyph_a: str, glyph_b: str):
        """Entangle two glyph IDs bidirectionally"""
        self.entangled_pairs.append((glyph_a, glyph_b))
        self.entanglement_map.setdefault(glyph_a, []).append(glyph_b)
        self.entanglement_map.setdefault(glyph_b, []).append(glyph_a)

    def get_entangled(self, glyph_id: str) -> List[str]:
        """Return all glyphs entangled with the given glyph"""
        return self.entanglement_map.get(glyph_id, [])

    def is_entangled(self, glyph_a: str, glyph_b: str) -> bool:
        return glyph_b in self.entanglement_map.get(glyph_a, [])

    def break_entanglement(self, glyph_id: str):
        """Remove all entanglements for a given glyph"""
        linked = self.entanglement_map.pop(glyph_id, [])
        for other in linked:
            if other in self.entanglement_map:
                self.entanglement_map[other] = [g for g in self.entanglement_map[other] if g != glyph_id]
        self.entangled_pairs = [pair for pair in self.entangled_pairs if glyph_id not in pair]


# Singleton instance
entangler_engine = EntanglerEngine()
