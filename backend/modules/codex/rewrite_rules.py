# File: backend/modules/codex/rewrite_rules.py
"""
Rewrite system for Codex + Symatics.

- Canonicalizes operators using CANONICAL_OPS.
- Applies normalization and simplification rules (logic, symatics).
- Provides a single entrypoint rewrite_tree(node).
"""

from backend.modules.codex.canonical_ops import CANONICAL_OPS
from backend.symatics import rewrite_rules as sym_rewrite
from backend.symatics.adapter import codex_ast_to_sym, sym_to_codex_ast


def _local_simplify(node):
    """Codex local simplifications (fast-path, cheap checks)."""
    # ¬¬A → A
    if node["op"] == "logic:¬" and len(node["args"]) == 1:
        inner = node["args"][0]
        if isinstance(inner, dict) and inner.get("op") == "logic:¬":
            return inner["args"][0]

    # A ⊕ A → false
    if node["op"] == "logic:⊕" and len(node["args"]) == 2:
        a, b = node["args"]
        if a == b:
            return {"op": "logic:false"}

    # A ∨ A → A
    if node["op"] == "logic:∨" and len(node["args"]) == 2:
        a, b = node["args"]
        if a == b:
            return a

    # A ∧ A → A
    if node["op"] == "logic:∧" and len(node["args"]) == 2:
        a, b = node["args"]
        if a == b:
            return a

    return node


def rewrite_tree(node, use_symatics: bool = True):
    """
    Normalize + simplify AST node.

    Args:
        node: Codex AST ({op, args}) or literal.
        use_symatics: if True, roundtrip through Symatics rewriter.
    Returns:
        Rewritten AST node.
    """
    if not isinstance(node, dict) or "op" not in node:
        return node

    # Canonicalize operator
    op = node["op"]
    node["op"] = CANONICAL_OPS.get(op, op)

    # Recurse on args
    args = node.get("args", [])
    node["args"] = [rewrite_tree(arg, use_symatics=use_symatics) for arg in args]

    # Local Codex simplifications
    node = _local_simplify(node)

    if use_symatics:
        try:
            # Roundtrip into Symatics rewriter
            sym_term = codex_ast_to_sym(node)
            sym_norm = sym_rewrite.simplify(sym_term)
            return sym_to_codex_ast(sym_norm)
        except Exception:
            # Fail safe → keep Codex node
            return node

    return node