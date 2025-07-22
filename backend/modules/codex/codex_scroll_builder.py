# backend/modules/codex/codex_scroll_builder.py

from typing import List, Dict

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

        # Build line
        line = "    " * indent + f"{symbol}: {value}"
        if action:
            line += f" => {action}"
        if include_coords and coord:
            line += f"    # coord: {coord}"

        lines.append(line)

        # Recurse into children
        if children:
            child_lines = build_codex_scroll(children, include_coords=include_coords, indent=indent + 1)
            lines.append(child_lines)

    return "\n".join(lines)


# Example entry point
if __name__ == "__main__":
    from backend.modules.glyphos.glyph_parser import parse_codexlang_string

    test_string = "Memory:Emotion = Joy => Store -> Memory:Emotion = Peace => Remember"
    parsed = parse_codexlang_string(test_string)
    tree = parsed.get("tree", [])

    scroll = build_codex_scroll(tree, include_coords=True)
    print("--- Codex Scroll ---")
    print(scroll)