# pattern_utils.py

from typing import Any, List, Dict


def extract_all_glyphs(symbolic_tree: Dict[str, Any]) -> List[Any]:
    """
    Recursively extract all glyphs from a symbolic_tree structure,
    including deeply nested expression glyphs.
    """
    extracted = []

    def recurse(glyph: Any):
        if isinstance(glyph, dict):
            if glyph.get("type") == "expression" and isinstance(glyph.get("glyphs"), list):
                for subglyph in glyph["glyphs"]:
                    recurse(subglyph)
            else:
                extracted.append(glyph)

    nodes = symbolic_tree.get("nodes", [])
    for node in nodes:
        glyph = node.get("glyph")
        if glyph:
            recurse(glyph)

    return extracted