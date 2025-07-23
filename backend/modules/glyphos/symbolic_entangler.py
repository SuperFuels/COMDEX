# File: backend/modules/glyphos/symbolic_entangler.py

from typing import Dict

# Runtime entanglement registry (in-memory)
entangled_pairs = []

def entangle_glyphs(glyph1: str, glyph2: str) -> Dict[str, str]:
    """
    Symbolically entangles two glyphs. Future actions on one may influence the other.
    """
    pair = {"glyph1": glyph1, "glyph2": glyph2}
    entangled_pairs.append(pair)
    return pair

def get_entangled_for(glyph: str) -> list[str]:
    """
    Returns all glyphs entangled with the given one.
    """
    return [
        p["glyph2"] if p["glyph1"] == glyph else p["glyph1"]
        for p in entangled_pairs
        if glyph in (p["glyph1"], p["glyph2"])
    ]