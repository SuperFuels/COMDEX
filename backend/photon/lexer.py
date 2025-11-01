# backend/photon/lexer.py
"""
Minimal Photon text -> glyph stream converter
"""

from typing import List, Dict
from backend.codexcore_virtual.instruction_metadata_bridge import OPERATOR_METADATA

# include alphanumeric + underscores as symbols
def tokenize(text: str) -> List[str]:
    buf, tokens = "", []
    for ch in text:
        if ch.isspace():
            if buf: tokens.append(buf); buf = ""
        elif ch in OPERATOR_METADATA:
            if buf: tokens.append(buf); buf = ""
            tokens.append(ch)
        else:
            buf += ch
    if buf: tokens.append(buf)
    return tokens

def to_glyph(tok: str) -> Dict:
    # operator?
    if tok in OPERATOR_METADATA:
        meta = OPERATOR_METADATA[tok]
        return {
            "text": tok,
            "type": meta["type"],
            "domain": meta["domain"],
            "name": meta["name"],
        }
    # primitive or literal
    return {"text": tok, "type": "literal"}

def text_to_glyphs(text: str) -> List[Dict]:
    return [to_glyph(t) for t in tokenize(text)]