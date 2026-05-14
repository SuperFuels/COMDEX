from typing import List, Dict, Any
from backend.codexcore_virtual.instruction_metadata_bridge import OPERATOR_METADATA

VALID_SYMBOLS = set(OPERATOR_METADATA.keys())

def validate_glyphs(glyphs: List[Dict[str, Any]]):
    errors = []
    for g in glyphs:
        txt = g.get("text", "").strip()
        if txt not in VALID_SYMBOLS and not txt.isalnum():
            errors.append({
                "glyph": txt,
                "error": "unknown_symbol",
                "msg": f"Unrecognized glyph '{txt}'"
            })
    return errors