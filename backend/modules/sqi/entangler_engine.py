# ============================================================
# 📁 backend/modules/sqi/entangler_engine.py
# ============================================================

"""
EntanglerEngine
===============

Symbolic entanglement management for SQI runtime.
Manages non-local relationships between Q-Glyphs and provides
fast lookup utilities for collapse propagation and observer logic.
"""

from typing import Dict, List, Tuple

class EntanglerEngine:
    """
    Symbolic Entangler Engine for SQI.
    Links two or more Q-Glyphs together in non-local resonance.
    """

    def __init__(self):
        self.entangled_pairs: List[Tuple[str, str]] = []
        self.entanglement_map: Dict[str, List[str]] = {}

    # ──────────────────────────────────────────────
    #  Core Entanglement Operations
    # ──────────────────────────────────────────────
    def entangle(self, glyph_a: str, glyph_b: str):
        """Entangle two glyph IDs bidirectionally."""
        self.entangled_pairs.append((glyph_a, glyph_b))
        self.entanglement_map.setdefault(glyph_a, []).append(glyph_b)
        self.entanglement_map.setdefault(glyph_b, []).append(glyph_a)

    def get_entangled(self, glyph_id: str) -> List[str]:
        """Return all glyphs entangled with the given glyph."""
        return self.entanglement_map.get(glyph_id, [])

    def is_entangled(self, glyph_a: str, glyph_b: str) -> bool:
        """Check whether two glyphs are entangled."""
        return glyph_b in self.entanglement_map.get(glyph_a, [])

    def break_entanglement(self, glyph_id: str):
        """Remove all entanglements for a given glyph."""
        linked = self.entanglement_map.pop(glyph_id, [])
        for other in linked:
            if other in self.entanglement_map:
                self.entanglement_map[other] = [
                    g for g in self.entanglement_map[other] if g != glyph_id
                ]
        self.entangled_pairs = [
            pair for pair in self.entangled_pairs if glyph_id not in pair
        ]

    def resolve_entanglement(self, glyph_id: str) -> List[str]:
        """
        Recursively resolve all glyphs entangled with the given one.
        Returns a flattened list (including the original glyph_id).
        """
        visited = set()
        queue = [glyph_id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            queue.extend(self.entanglement_map.get(current, []))

        return list(visited)


# ──────────────────────────────────────────────
#  Singleton instance + Functional Wrappers
# ──────────────────────────────────────────────
entangler_engine = EntanglerEngine()


def is_entangled(glyph_a: str, glyph_b: str) -> bool:
    """Functional shortcut to check entanglement between two glyphs."""
    return entangler_engine.is_entangled(glyph_a, glyph_b)


def resolve_entanglement(glyph_id: str) -> List[str]:
    """Functional shortcut to resolve all entangled glyphs for a given ID."""
    return entangler_engine.resolve_entanglement(glyph_id)