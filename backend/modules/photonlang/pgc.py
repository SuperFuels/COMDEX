# backend/modules/photonlang/pgc.py
"""
Photon Grammar Compiler (PGC)
Pure glyph -> PhotonLang AST bridge
"""

from __future__ import annotations
from typing import List, Dict, Any
import re

from .parser import (
    Program, GlyphInit, Assign, Call, Attr, Name, Literal,
    SendThrough, SaveAs, ImportStmt, FromImport, WormholeImport
)

GLYPH_CHARS = "⊕↔⟲μπ->∇⧖"

glyph_pattern = re.compile(f"[{GLYPH_CHARS}]+")
param_pattern = re.compile(r"\{([^}]*)\}")

def tokenize_glyphs(src: str) -> List[Dict[str, Any]]:
    tokens = []
    for line in src.splitlines():
        line = line.strip()
        if not line:
            continue

        m = glyph_pattern.match(line)
        if not m:
            continue

        seq = m.group(0)

        params = {}
        pm = param_pattern.search(line)
        if pm:
            raw = pm.group(1)
            for kv in raw.split(","):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    try:
                        v = float(v)
                    except:
                        pass
                    params[k.strip()] = v

        tokens.append({"seq": seq, "params": params})

    return tokens


def glyphs_to_ast(tokens: List[Dict[str, Any]]) -> Program:
    """
    Convert glyph stream -> Program with GlyphInit + optional calls
    """
    stmts = []
    for t in tokens:
        seq = t["seq"]
        params = t["params"]

        # base glyph-init node
        stmts.append(GlyphInit(seq=seq))

        # ⧖ modulation becomes: QuantumFieldCanvas().resonate(...) or param mix
        if "⧖" in seq and params:
            # translator to call form: QFC().resonate("", freq=..., amp=...)
            # AST = Call(Attr(Name("QuantumFieldCanvas"), "resonate"), args=[...])
            call = Call(
                func=Attr(obj=Call(func=Name("QuantumFieldCanvas"), args=[]), name="resonate"),
                args=[(None, Literal(""))] + [(k, Literal(v)) for k, v in params.items()]
            )
            stmts.append(call)

    return Program(stmts=stmts)


def compile_photon(src: str) -> Program:
    tokens = tokenize_glyphs(src)
    if not tokens:
        # Return empty stub program so interpreter falls back to text parser
        return Program(stmts=[])
    return glyphs_to_ast(tokens)


def is_pure_glyph_program(src: str) -> bool:
    stripped = src.strip().replace(" ", "")
    return bool(glyph_pattern.fullmatch(stripped) or glyph_pattern.search(stripped))