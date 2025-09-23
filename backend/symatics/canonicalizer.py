# backend/symatics/canonicalizer.py
# ---------------------------------------------------------------------
# Canonicalizer for Symatics expressions
# - Converts arbitrary expression trees into canonical tuple form
# - Used by rewrite rules, law checks, and equivalence testing
# ---------------------------------------------------------------------

from __future__ import annotations
from typing import Any


def _canonical(expr: Any) -> Any:
    """
    Internal canonicalization of symbolic expressions.
    Applies normalization rules, ordering, and deduplication.

    Rules:
      • Constants stringified ("0","1","2",...) unless preserved in ∫
      • ∫ returns ("∫", const, var) with const as int if numeric
      • Δ returns fully canonicalized derivative body
      • Commutative ops (+,*) get sorted args
    """
    from backend.symatics.rewrite_rules import simplify
    expr = simplify(expr)

    if isinstance(expr, dict):
        op = expr.get("op")
        args = expr.get("args", [])

        # --- integration node ---
        if op == "∫":
            if expr.get("simplified") is not None:
                return _canonical(expr["simplified"])
            arg0 = _canonical(args[0])
            arg1 = args[1]
            # Preserve raw int for ∫ constant law
            if isinstance(arg0, str) and arg0.lstrip("-").isdigit():
                arg0 = int(arg0)
            if isinstance(arg0, (dict, tuple)) and arg0 == ("const",):
                arg0 = 0
            return ("∫", arg0, arg1)

        # --- derivative node ---
        if op == "Δ":
            if expr.get("simplified") is not None:
                return _canonical(expr["simplified"])
            return ("Δ", _canonical(args[0]), args[1])

        # --- multiplication (commutative) ---
        if op in {"*", "mul"}:
            def sort_key(x):
                if isinstance(x, str) and x.lstrip("-").isdigit():
                    return (0, int(x))
                if isinstance(x, tuple) and x[0] == "const":
                    try:
                        return (0, int(x[1]))
                    except Exception:
                        return (0, str(x[1]))
                return (1, str(x))

            can_args = tuple(sorted((_canonical(a) for a in args), key=sort_key))
            return ("mul", can_args)

        # --- division ---
        if op in {"/", "div"}:
            return ("/", tuple(_canonical(a) for a in args))

        # --- addition (commutative) ---
        if op == "+":
            return ("+", tuple(sorted((_canonical(a) for a in args), key=str)))

        # --- powers ---
        if op in {"^", "pow"}:
            return ("^", tuple(_canonical(a) for a in args))

        # --- var / const ---
        if op == "var":
            return ("var", args[0] if args else None)
        if op == "const":
            val = args[0] if args else None
            return str(val) if val is not None else "0"

        # --- generic ops ---
        return (op, tuple(_canonical(a) for a in args))

    # --- list/tuple fallback ---
    if isinstance(expr, (list, tuple)):
        return tuple(_canonical(x) for x in expr)

    # --- number base cases ---
    if isinstance(expr, (int, float)):
        return str(expr)
    if isinstance(expr, str) and expr.lstrip("-").isdigit():
        return str(expr)

    return expr


def canonical(expr: Any) -> Any:
    """
    Public wrapper for canonicalization.
    Other modules should import this instead of _canonical.
    """
    return _canonical(expr)


# Public API
__all__ = ["canonical"]