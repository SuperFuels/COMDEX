"""
Symatics ↔ Codex AST Adapter
----------------------------

Bridges CodexLang canonical ASTs ({op, args, ...}) with Symatics Terms
(Var, Sym, App) used in Symatics rewriter.

Allows:
    - Feeding Codex AST into Symatics rewriter.
    - Converting Symatics Terms back to Codex AST for runtime/executor.

This prevents schema drift: Codex, GlyphOS, and Symatics all share
the canonical {op: "domain:symbol", args: []} shape, with optional metadata.
"""

from typing import Dict, Any
from backend.symatics.terms import Var, Sym, App, Term

# --------------------------
# Codex → Symatics
# --------------------------

def codex_ast_to_sym(node: Dict[str, Any]) -> Term:
    """Convert Codex AST node {op, args, ...} → Symatics Term."""
    if node is None:
        return Sym("⊥")

    if not isinstance(node, dict):
        # treat bare strings/numbers as variables or constants
        return Var(str(node))

    op = node.get("op")
    args = node.get("args", [])

    # Literals
    if op == "lit":
        return Var(str(node["value"]))

    # Bottom
    if op in ("⊥", "logic:⊥"):
        return Sym("⊥")

    # Extract extra metadata (phase, amplitude, etc.)
    extra = {k: v for k, v in node.items() if k not in {"op", "args", "value"}}
    if not extra:
        extra = None

    # General operator → App(Sym(op), args, attrs)
    return App(Sym(op), [codex_ast_to_sym(a) for a in args], attrs=extra)


# --------------------------
# Symatics → Codex
# --------------------------

def sym_to_codex_ast(expr: Term) -> Dict[str, Any]:
    """Convert Symatics Term → Codex canonical AST dict."""
    if isinstance(expr, Var):
        return {"op": "lit", "value": expr.name}

    if isinstance(expr, Sym):
        if expr.name == "⊥":
            return {"op": "logic:⊥", "args": []}
        return {"op": expr.name, "args": []}

    if isinstance(expr, App):
        head = expr.head
        if isinstance(head, Sym):
            op = head.name
        else:
            # nested App as head (rare) → convert recursively
            op_ast = sym_to_codex_ast(head)
            op = op_ast.get("op", "lit")

        node = {
            "op": op,
            "args": [sym_to_codex_ast(a) for a in expr.args],
        }

        # Reattach metadata if present
        if expr.attrs:
            node.update(expr.attrs)

        return node

    raise TypeError(f"Unsupported Symatics term type: {type(expr)}")