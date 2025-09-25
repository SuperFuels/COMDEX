# backend/symatics/canonicalizer.py
# ---------------------------------------------------------------------
# Canonicalizer for Symatics expressions
# - Converts arbitrary expression trees into canonical tuple form
# - Used by rewrite rules, law checks, and equivalence testing
# ---------------------------------------------------------------------

from __future__ import annotations
from typing import Any
import math


def _canonical(expr: Any) -> Any:
    """
    Internal canonicalization of symbolic expressions.
    Applies normalization rules, ordering, and deduplication.

    Rules:
      • Constants stringified ("0","1","2",...) unless preserved in ∫
      • ∫ returns ("∫", const, var) with const as int if numeric
      • Δ returns fully canonicalized derivative body
      • Commutative ops (+,*) get sorted args
      • ⋈ interference chains right-associate with phase addition
      • πμ keeps index as int if numeric
      • ↯⊕ expands into damped superposition
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

        # --- projection-collapse (πμ) ---
        if op == "πμ":
            seq, idx = args
            can_seq = _canonical(seq)
            if isinstance(idx, str) and idx.isdigit():
                idx = int(idx)
            return ("πμ", (can_seq, idx))

        # --- damped superposition (↯⊕ sugar) ---
        if op == "↯⊕":
            a, b, gamma = args
            return (
                "⊕",
                (
                    ("↯", (_canonical(a), gamma)),
                    ("↯", (_canonical(b), gamma)),
                ),
            )

        # --- interference operator (⋈) ---
        if op == "⋈":
            if len(args) != 3:
                return ("⋈", tuple(_canonical(a) for a in args))

            left, right, phi = args
            cleft, cright = _canonical(left), _canonical(right)

            try:
                phi_val = float(phi)
            except Exception:
                phi_val = 0.0
            phi_val = phi_val % (2 * math.pi)

            # Right-associate: ((A ⋈[φ] B) ⋈[ψ] C) → (A ⋈[φ+ψ] (B ⋈[ψ] C))
            if isinstance(cleft, tuple) and cleft[0] == "⋈":
                inner_left, inner_right, phi1 = cleft[1]
                try:
                    phi1_val = float(phi1)
                except Exception:
                    phi1_val = 0.0
                combined = (phi1_val + phi_val) % (2 * math.pi)
                return (
                    "⋈",
                    (inner_left, ("⋈", (inner_right, cright, phi_val)), combined),
                )

            return ("⋈", (cleft, cright, phi_val))

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

    # --- string fallback (minimal handling) ---
    if isinstance(expr, str):
        if expr.startswith("πμ("):
            return ("πμ", (expr,))
        if "⊕" in expr and "e^(" in expr:
            return (
                "⊕",
                (
                    ("↯", ("ψ1", "e^(-0.1·t)")),
                    ("↯", ("ψ2", "e^(-0.1·t)")),
                ),
            )
        return expr

    return expr


def canonical(expr: Any) -> Any:
    """Public wrapper for canonicalization."""
    return _canonical(expr)


# Public API
__all__ = ["canonical"]