from __future__ import annotations

"""
EntanglerEngine
===============

Symbolic entanglement management for SQI runtime.
Manages non-local relationships between Q-Glyphs and provides
fast lookup utilities for collapse propagation and observer logic.
"""

from typing import Dict, List, Tuple, Optional
import os


def _quiet_enabled() -> bool:
    return os.getenv("TESSARIS_TEST_QUIET") == "1" or os.getenv("TESSARIS_DETERMINISTIC_TIME") == "1"


class EntanglerEngine:
    """
    Symbolic Entangler Engine for SQI.
    Links two or more Q-Glyphs together in non-local resonance.
    """

    def __init__(self):
        self.entangled_pairs: List[Tuple[str, str]] = []
        self.entanglement_map: Dict[str, List[str]] = {}

    def entangle(self, glyph_a: str, glyph_b: str) -> None:
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

    def break_entanglement(self, glyph_id: str) -> None:
        """Remove all entanglements for a given glyph."""
        linked = self.entanglement_map.pop(glyph_id, [])
        for other in linked:
            if other in self.entanglement_map:
                self.entanglement_map[other] = [g for g in self.entanglement_map[other] if g != glyph_id]
        self.entangled_pairs = [pair for pair in self.entangled_pairs if glyph_id not in pair]

    def resolve_entanglement(self, glyph_id: str) -> List[str]:
        """
        Recursively resolve all glyphs entangled with the given one.
        Returns a flattened list (including the original glyph_id).
        """
        visited: set[str] = set()
        queue: List[str] = [glyph_id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            queue.extend(self.entanglement_map.get(current, []))

        return list(visited)


# ──────────────────────────────────────────────
# Lazy singleton (no import-time runtime bring-up)
# ──────────────────────────────────────────────
_ENTANGLER: Optional[EntanglerEngine] = None


def get_entangler_engine() -> EntanglerEngine:
    global _ENTANGLER
    if _ENTANGLER is None:
        _ENTANGLER = EntanglerEngine()
        if not _quiet_enabled():
            print("[SQI] EntanglerEngine initialized (lazy)")
    return _ENTANGLER


class _EntanglerProxy:
    def __getattr__(self, name: str):
        return getattr(get_entangler_engine(), name)


# Back-compat: allow `from ... import entangler_engine`
entangler_engine = _EntanglerProxy()


def is_entangled(glyph_a: str, glyph_b: str) -> bool:
    return get_entangler_engine().is_entangled(glyph_a, glyph_b)


def resolve_entanglement(glyph_id: str) -> List[str]:
    return get_entangler_engine().resolve_entanglement(glyph_id)
