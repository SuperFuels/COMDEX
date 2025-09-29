# backend/modules/codex/rewrite_rules.py

"""
Rewrite system for Codex + Symatics.

- Canonicalizes operators using CANONICAL_OPS.
- Applies normalization and simplification rules (logic, symatics).
- Provides a single entrypoint rewrite_tree(node).
"""

from backend.modules.codex.canonical_ops import CANONICAL_OPS


def rewrite_tree(node):
    """
    Normalize + simplify AST node in place.

    Args:
        node (dict | str | other): AST node or literal.
    Returns:
        dict | str: Rewritten node.
    """
    if not isinstance(node, dict) or "op" not in node:
        return node

    # Canonicalize operator
    op = node["op"]
    node["op"] = CANONICAL_OPS.get(op, op)

    # Recurse on args
    args = node.get("args", [])
    node["args"] = [rewrite_tree(arg) for arg in args]

    # Simplification rules
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