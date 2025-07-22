# File: backend/modules/codex/codex_scroll_builder.py

from typing import List, Dict, Optional, Any
from backend.modules.codex.codex_metrics import score_glyph_tree  # Optional import for scoring
from backend.modules.glyphos.glyph_parser import parse_codexlang_string

def build_codex_scroll(glyph_tree: List[Dict], include_coords: bool = False, indent: int = 0) -> str:
    """
    Converts structured glyph tree into CodexLang scroll format.
    Recursively traverses tree and renders symbolic logic.
    """
    lines = []

    for glyph in glyph_tree:
        symbol = glyph.get("symbol", "???")
        value = glyph.get("value", "undefined")
        action = glyph.get("action", "")
        children = glyph.get("children", [])
        coord = glyph.get("coord")

        # Build base line
        line = "    " * indent + f"{symbol}: {value}"
        if action:
            line += f" => {action}"
        if include_coords and coord:
            line += f"    # coord: {coord}"

        lines.append(line)

        # Recurse
        if children:
            child_lines = build_codex_scroll(children, include_coords=include_coords, indent=indent + 1)
            lines.append(child_lines)

    return "\n".join(lines)


def build_scroll_from_glyph(glyph_tree: List[Dict[str, Any]]) -> str:
    """
    ✅ Entry point used by memory_engine and runtime systems.
    Wraps build_codex_scroll and hides internal config flags.
    """
    return build_codex_scroll(glyph_tree, include_coords=True)


# Example test runner
if __name__ == "__main__":
    test_string = "Memory:Emotion = Joy => Store -> Memory:Emotion = Peace => Remember"
    parsed = parse_codexlang_string(test_string)
    tree = parsed.get("tree", [])

    scroll = build_scroll_from_glyph(tree)
    print("--- Codex Scroll ---")
    print(scroll)