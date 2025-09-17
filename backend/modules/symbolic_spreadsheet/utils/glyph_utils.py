# File: backend/modules/symbolic_spreadsheet/utils/glyph_utils.py

from typing import List, Dict
from backend.modules.glyphos.glyph_tokenizer import tokenize_symbol_text_to_glyphs

def parse_logic_to_glyphs(logic: str) -> List[Dict[str, str]]:
    """
    Converts logic string like 'x + 2' or 'sin(y)' into structured glyphs.
    Delegates to glyph_tokenizer and adds normalization.
    """
    raw_tokens = tokenize_symbol_text_to_glyphs(logic)
    normalized = []

    for token in raw_tokens:
        token_type = token["type"]
        value = token["value"]

        if token_type == "bracket":
            token_type = "paren"
        elif token_type == "variable" and value in {"sin", "cos", "tan", "log", "exp"}:
            token_type = "function"

        normalized.append({"type": token_type, "value": value})

    return normalized