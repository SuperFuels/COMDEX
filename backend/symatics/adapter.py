# File: symatics/adapter.py
"""
Symatics ↔ Codex AST Adapter
----------------------------

Bridges CodexLang canonical ASTs ({op, args}) with Symatics Expr dataclasses.

Allows:
    - Feeding Codex AST into Symatics rewriter.
    - Converting Symatics Expr back to Codex AST for runtime/executor.

This prevents schema drift: Codex, GlyphOS, and Symatics all share
the canonical {op: "domain:symbol", args: []} shape.
"""

from typing import Dict, Any, Union
from backend.symatics import rewriter as sym

# --------------------------
# Codex → Symatics
# --------------------------

def codex_ast_to_sym(node: Dict[str, Any]) -> sym.Expr:
    """Convert Codex AST node {op, args} → Symatics Expr."""
    if node is None:
        return sym.Bot()

    op = node.get("op")
    args = node.get("args", [])

    # Literals
    if op == "lit":
        return sym.Atom(node["value"])

    # Special bottom
    if op in ("⊥", "logic:⊥"):
        return sym.Bot()

    # Constructive / destructive interference
    if op.endswith("⊕"):
        return sym.SymAdd(codex_ast_to_sym(args[0]), codex_ast_to_sym(args[1]))
    if op.endswith("⊖"):
        return sym.SymSub(codex_ast_to_sym(args[0]), codex_ast_to_sym(args[1]))

    # General interference connective
    if op.endswith("⋈"):
        # Expected shape: {op:"interf:⋈", args:[left,right], phase:float}
        φ = node.get("phase", 0.0)
        return sym.Interf(φ, codex_ast_to_sym(args[0]), codex_ast_to_sym(args[1]))

    # Default: treat as atom
    if "value" in node:
        return sym.Atom(node["value"])

    return sym.Atom(op)


# --------------------------
# Symatics → Codex
# --------------------------

def sym_to_codex_ast(expr: sym.Expr) -> Dict[str, Any]:
    """Convert Symatics Expr → Codex canonical AST dict."""
    if isinstance(expr, sym.Atom):
        return {"op": "lit", "value": expr.name}

    if isinstance(expr, sym.Bot):
        return {"op": "logic:⊥", "args": []}

    if isinstance(expr, sym.SymAdd):
        return {
            "op": "logic:⊕",
            "args": [sym_to_codex_ast(expr.left), sym_to_codex_ast(expr.right)],
        }

    if isinstance(expr, sym.SymSub):
        return {
            "op": "logic:⊖",
            "args": [sym_to_codex_ast(expr.left), sym_to_codex_ast(expr.right)],
        }

    if isinstance(expr, sym.Interf):
        return {
            "op": "interf:⋈",
            "phase": expr.phase,
            "args": [sym_to_codex_ast(expr.left), sym_to_codex_ast(expr.right)],
        }

    raise TypeError(f"Unsupported Symatics expr type: {type(expr)}")