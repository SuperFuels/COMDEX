# glyph_util.py
# Utilities for GlyphOS encoding and decoding

import re
from typing import Dict, List, Union
from glyph_parser import GlyphParser, StructuredGlyph


def encode_structured_glyph(glyph_data: Dict) -> str:
    """
    Convert a glyph dict into GlyphOS string syntax:
    ⟦ Type | Target : Value -> Action ⟧
    """
    try:
        g_type = glyph_data.get("type", "Unknown")
        target = glyph_data.get("target", "Object")
        value = glyph_data.get("value", "Unknown")
        action = glyph_data.get("action", "Reflect")
        return f"⟦ {g_type} | {target} : {value} -> {action} ⟧"
    except Exception as e:
        return f"[Error encoding glyph: {e}]"


def batch_parse_glyphs(input_text: str) -> List[Dict]:
    """
    Parses mixed input containing both:
    - Symbol glyphs (e.g., ✦⚛🧭)
    - Structured glyphs (e.g., ⟦ Type | Target : Value -> Action ⟧)
    
    Returns a unified list of parsed glyph dicts.
    """
    structured_pattern = r"(⟦.*?⟧)"
    chunks = re.split(structured_pattern, input_text.strip())
    parsed = []

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        if chunk.startswith("⟦") and chunk.endswith("⟧"):
            sg = StructuredGlyph(chunk)
            parsed.append(sg.to_dict())
        else:
            # Parse individual symbols
            gp = GlyphParser(chunk)
            parsed.extend(gp.parse())

    return parsed


# 🧪 Test if run directly
if __name__ == "__main__":
    sample_dict = {
        "type": "Write",
        "target": "Glyph",
        "value": "Self",
        "action": "⬁"
    }
    print("Encoded:", encode_structured_glyph(sample_dict))

    test_input = "⚛ ⟦ Write | Glyph : Self -> ⬁ ⟧ ✦"
    print("Batch Parsed:")
    for g in batch_parse_glyphs(test_input):
        print(g)