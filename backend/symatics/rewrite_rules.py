"""
Symatics Rewrite Rules
─────────────────────────────────────────────
Enforces algebraic laws by simplifying expressions via rewrites.
"""

from typing import Any, Dict, List, Union

SymExpr = Union[str, Dict[str, Any], List[Any]]

# ──────────────────────────────
# Rewrite Rules
# ──────────────────────────────

def rewrite_idempotence(expr: SymExpr) -> SymExpr:
    """a ⊕ a → a ; a ↔ a → a"""
    if not isinstance(expr, dict):
        return expr
    if expr.get("op") in {"⊕", "↔"}:
        args = expr.get("args", [])
        if len(args) == 2 and args[0] == args[1]:
            return args[0]
    return expr


def rewrite_identity(expr: SymExpr) -> SymExpr:
    """Identity: a ⊕ ∅ = a ; ⊕ with None collapses."""
    if not isinstance(expr, dict):
        return expr
    if expr.get("op") == "⊕":
        args = [a for a in expr.get("args", []) if a not in (None, "∅")]
        if len(args) == 1:
            return args[0]
        expr = expr.copy()
        expr["args"] = args
        expr["state"] = args
    return expr


def rewrite_commutativity(expr: SymExpr) -> SymExpr:
    """Sort args for commutative ops after simplification."""
    if not isinstance(expr, dict):
        return expr
    if expr.get("op") in {"⊕", "↔"}:
        from backend.symatics.rewrite_rules import simplify
        args = [simplify(a) for a in expr.get("args", [])]
        expr = expr.copy()
        expr["args"] = sorted(args, key=lambda x: str(x))
        expr["state"] = expr["args"]
    return expr


def rewrite_associativity(expr: SymExpr) -> SymExpr:
    """Recursively flatten nested ⊕ trees into a single flat list."""
    if not isinstance(expr, dict):
        return expr
    if expr.get("op") == "⊕":
        flat_args = []
        for arg in expr.get("args", []):
            if isinstance(arg, dict) and arg.get("op") == "⊕":
                # recursively simplify the inner ⊕ before extracting
                from backend.symatics.rewrite_rules import simplify
                inner = simplify(arg)
                if isinstance(inner, dict) and inner.get("op") == "⊕":
                    flat_args.extend(inner.get("args", []))
                else:
                    flat_args.append(inner)
            else:
                flat_args.append(arg)
        expr = expr.copy()
        expr["args"] = flat_args
        expr["state"] = flat_args
    return expr


def rewrite_distributivity(expr: SymExpr) -> SymExpr:
    """a ⊕ (b ↔ c) → (a ⊕ b) ↔ (a ⊕ c)."""
    if not isinstance(expr, dict):
        return expr
    if expr.get("op") == "⊕":
        args = expr.get("args", [])
        if len(args) == 2 and isinstance(args[1], dict) and args[1].get("op") == "↔":
            a, (b, c) = args[0], args[1]["args"]
            return {
                "op": "↔",
                "args": [
                    {"op": "⊕", "args": [a, b], "state": [a, b]},
                    {"op": "⊕", "args": [a, c], "state": [a, c]},
                ],
            }
    return expr


def rewrite_constant_folding(expr: SymExpr) -> SymExpr:
    """
    Fold numeric constants for arithmetic operators only (e.g. '+').
    DO NOT fold for Symatics superposition ⊕ — it's not numeric addition.
    """
    if not isinstance(expr, dict):
        return expr

    op = expr.get("op")
    args = expr.get("args", [])

    # Arithmetic folding (safe)
    if op in {"+", "add"}:
        if all(isinstance(x, str) and x.isdigit() for x in args):
            val = sum(int(x) for x in args)
            return str(val)
        return expr

    # Explicitly do nothing for ⊕ (superposition)
    if op == "⊕":
        return expr

    return expr


# ──────────────────────────────
# Rule Engine
# ──────────────────────────────

RULES = [
    rewrite_idempotence,
    rewrite_identity,
    rewrite_associativity,
    rewrite_distributivity,
    rewrite_constant_folding,
    rewrite_commutativity,  # keep last for stable canonical order
]

def normalize(expr: SymExpr) -> SymExpr:
    """
    Apply rewrite rules repeatedly until a fixed point is reached.
    Handles both atomic values (str/int) and dict expressions.
    """
    changed = True
    while changed:
        changed = False
        for rule in RULES:
            new_expr = rule(expr)
            if new_expr != expr:
                expr = new_expr
                changed = True
    return expr


def simplify(expr: SymExpr) -> SymExpr:
    """Public API for Symatics simplification."""
    return normalize(expr)