# ===============================
# 📁 backend/quant/qlang/qlang_parser.py
# ===============================
"""
💡 QLang Parser - Symbolic Syntax Front-End
-------------------------------------------
Parses QLang / Photon Language expressions into
intermediate QGraph (via QCompilerCore).

Supports symbolic operators from Symatics Algebra:
    ⊕  superpose
    ↔  entangle
    ⟲  resonate
    ∇  collapse
    μ  measure
    π  project

Now Unicode-aware for photon/glyph identifiers:
    ψ, Φ, φ, Ψ, μπ, etc.
"""

from __future__ import annotations
import re
from typing import Dict, Any, List

from backend.quant.qcompiler.qcompiler_core import QCompilerCore


# ----------------------------------------------------------------------
# Token patterns and helpers
# ----------------------------------------------------------------------
TOKEN_SPEC = [
    ("SUPERPOSE",  r"⊕|superpose"),
    ("ENTANGLE",   r"↔|entangle"),
    ("RESONATE",   r"⟲|resonate"),
    ("COLLAPSE",   r"∇|collapse"),
    ("MEASURE",    r"μ|measure"),
    ("PROJECT",    r"π|project"),
    ("ASSIGN",     r"="),
    ("NUMBER",     r"\b\d+(\.\d+)?\b"),
    # Allow Unicode Greek letters (ψ Φ φ Ψ μπ) as valid identifiers
    ("IDENT",      r"[A-Za-z_ψΦφΨμπ][A-Za-z0-9_ψΦφΨμπ]*"),
    ("OP",         r"[\+\-\*/]"),
    ("LPAREN",     r"\("),
    ("RPAREN",     r"\)"),
    ("COMMENT",    r"#.*"),
    ("SKIP",       r"[ \t\r\n]+"),
    ("MISMATCH",   r"."),
]
TOKEN_REGEX = re.compile("|".join(f"(?P<{n}>{p})" for n, p in TOKEN_SPEC))


# ----------------------------------------------------------------------
# Tokenizer
# ----------------------------------------------------------------------
def tokenize(src: str) -> List[Dict[str, str]]:
    """Convert source code into token list, Unicode-safe."""
    tokens: List[Dict[str, str]] = []
    for m in TOKEN_REGEX.finditer(src):
        kind = m.lastgroup
        value = m.group()
        if kind in ("SKIP", "COMMENT"):
            continue
        elif kind == "MISMATCH":
            raise SyntaxError(f"Unexpected token {value!r}")
        # Normalize common Greek identifiers to ascii-safe names
        if kind == "IDENT":
            value = (
                value.replace("ψ", "psi")
                     .replace("Ψ", "Psi")
                     .replace("Φ", "Phi")
                     .replace("φ", "phi")
                     .replace("μ", "mu")
                     .replace("π", "pi")
            )
        tokens.append({"type": kind, "value": value})
    return tokens


# ----------------------------------------------------------------------
# Parser / Evaluator
# ----------------------------------------------------------------------
class QLangParser:
    """
    Converts symbolic source -> QCompilerCore graph.
    """

    def __init__(self):
        self.compiler = QCompilerCore()

    # --------------------------------------------------------------
    def parse(self, src: str) -> Dict[str, Any]:
        """Main entry point: tokenize, normalize, compile."""
        toks = tokenize(src)
        norm = self._normalize_tokens(toks)
        graph = self.compiler.compile_expr(norm)
        return graph.to_dict()

    # --------------------------------------------------------------
    def _normalize_tokens(self, tokens: List[Dict[str, str]]) -> str:
        """
        Converts glyph operators to function-like expressions.
        e.g.  ψ1 ⊕ ψ2  ->  superpose(psi1, psi2)
        """
        out: List[str] = []
        i = 0
        while i < len(tokens):
            t = tokens[i]
            v = t["value"]
            typ = t["type"]

            if typ == "SUPERPOSE":
                a = out.pop() if out else "psi1"
                b = tokens[i + 1]["value"] if i + 1 < len(tokens) else "psi2"
                out.append(f"superpose({a},{b})")
                i += 1
            elif typ == "ENTANGLE":
                a = out.pop() if out else "psi1"
                b = tokens[i + 1]["value"] if i + 1 < len(tokens) else "psi2"
                out.append(f"entangle({a},{b})")
                i += 1
            elif typ == "RESONATE":
                a = out.pop() if out else "psi"
                out.append(f"resonate({a})")
            elif typ == "COLLAPSE":
                a = out.pop() if out else "psi"
                out.append(f"collapse({a})")
            elif typ == "MEASURE":
                a = out.pop() if out else "psi"
                out.append(f"measure({a})")
            elif typ == "PROJECT":
                a = out.pop() if out else "psi"
                out.append(f"project({a})")
            else:
                out.append(v)
            i += 1

        return " ".join(out)

    # --------------------------------------------------------------
    def run_test(self) -> Dict[str, Any]:
        """Quick round-trip test from QLang->Graph->Sim."""
        expr = "ψ1 ⊕ ψ2 ⟲ ψ1 ↔ ψ2 ∇ μ"
        toks = tokenize(expr)
        norm = self._normalize_tokens(toks)
        graph = self.compiler.compile_expr(norm)
        from backend.quant.qtensor.qtensor_field import random_field
        psi1, psi2 = random_field((4, 4)), random_field((4, 4))
        sim = self.compiler.simulate({"psi1": psi1, "psi2": psi2})
        return {
            "tokens": len(toks),
            "compiled_nodes": len(graph.nodes),
            "normalized": norm,
            "simulation": sim,
        }

    def compile_expr(self, expr):
        """
        Compile symbolic expression into QGraph.
        Accepts str (source code), dict (already parsed), or AST node.
        """
        import ast
        from backend.quant.qcompiler.qgraph import QGraph  # or wherever it's defined

        # If already a dict, wrap safely
        if isinstance(expr, dict):
            try:
                return QGraph.from_dict(expr)
            except Exception:
                # Try rebuilding from dict content
                g = QGraph()
                g.nodes.update(expr.get("nodes", {}))
                g.edges.update(expr.get("edges", {}))
                return g

        # If a plain string, parse to AST
        if isinstance(expr, str):
            try:
                node = ast.parse(expr, mode="eval")
            except SyntaxError:
                node = ast.parse(expr, mode="exec")
        else:
            node = expr  # already AST

        # Defensive fix: ensure node has _fields
        if not hasattr(node, "_fields"):
            raise TypeError(f"Invalid node type {type(node)} for compile_expr")

        # Proceed with standard graph build
        return self._build_graph(node)


# ----------------------------------------------------------------------
# Self-test
# ----------------------------------------------------------------------
if __name__ == "__main__":
    parser = QLangParser()
    from pprint import pprint
    pprint(parser.run_test())