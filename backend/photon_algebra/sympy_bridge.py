# -*- coding: utf-8 -*-
"""
Photon ↔ SymPy Bridge
=====================
Task: I2.1 - Define translation rules (Photon ↔ SymPy)

Provides bidirectional, lossless conversion between Photon Algebra JSON IR
and symbolic SymPy expressions for mathematical interop and simplification.

Modes:
    - lossless=True  -> preserve full photon semantics (custom symbols, ops)
    - lossless=False -> lower to SymPy booleans (for simplify(), CNF, SAT)

Operators:
    ⊕  -> Or
    ⊗  -> And
    ¬  -> Not
    ↔  -> Equivalent
    ★  -> PhotonStar (custom BooleanFunction)
    ⊖  -> PhotonMinus (custom BooleanFunction)
    ≈  -> PhotonApprox (custom BooleanFunction)
    ⊂  -> PhotonSubset (custom BooleanFunction)
Constants:
    ∅  -> PH_EMPTY
    ⊤  -> PH_TOP
    ⊥  -> PH_BOTTOM
"""

from __future__ import annotations
from typing import Any, Dict, Union
import sympy as sp
from sympy import Or, And, Not, Equivalent, Symbol
from sympy.logic.boolalg import BooleanFunction
from backend.photon_algebra.core import EMPTY, TOP, BOTTOM

Expr = Union[str, Dict[str, Any]]

# -------------------------------------------------------------------------
# Custom SymPy BooleanFunction types for lossless representation
# -------------------------------------------------------------------------
class PhotonStar(BooleanFunction):
    nargs = (1,)

    @classmethod
    def eval(cls, *args):
        return None


class PhotonMinus(BooleanFunction):
    nargs = (2,)

    @classmethod
    def eval(cls, *args):
        if len(args) != 2:
            return None
        return None


class PhotonApprox(BooleanFunction):
    nargs = (2,)

    @classmethod
    def eval(cls, *args):
        return None


class PhotonSubset(BooleanFunction):
    nargs = (2,)

    @classmethod
    def eval(cls, *args):
        if len(args) == 2 and args[0] == args[1]:
            return sp.S.true
        return None


# -------------------------------------------------------------------------
# Symbolic constants
# -------------------------------------------------------------------------
PH_EMPTY = Symbol("PH_EMPTY")
PH_TOP = Symbol("PH_TOP")
PH_BOTTOM = Symbol("PH_BOTTOM")

# -------------------------------------------------------------------------
# Helper: commutative operator set
# -------------------------------------------------------------------------
COMMUTATIVE_OPS = {"⊕", "⊗", "↔", "≈"}  # ⊖ and ⊂ are not commutative

# -------------------------------------------------------------------------
# Photon -> SymPy
# -------------------------------------------------------------------------
def to_sympy(node: Expr, *, lossless: bool = True) -> sp.Expr:
    """Convert a Photon IR expression into a SymPy expression (Boolean-safe)."""
    if isinstance(node, str):
        return Symbol(node)

    if not isinstance(node, dict):
        return node

    op = node.get("op")

    # ---- constants ----
    if op == "∅":
        return PH_EMPTY if lossless else sp.S.false
    if op == "⊤":
        return PH_TOP if lossless else sp.S.true
    if op == "⊥":
        return PH_BOTTOM if lossless else sp.S.false

    # ---- boolean ops ----
    if op == "⊕":
        parts = [to_sympy(s, lossless=lossless) for s in node.get("states", [])]
        return Or(*parts, evaluate=False)
    if op == "⊗":
        parts = [to_sympy(s, lossless=lossless) for s in node.get("states", [])]
        safe = [
            p if isinstance(p, sp.logic.boolalg.Boolean)
            else Symbol(str(p))
            for p in parts
        ]
        return And(*safe, evaluate=False)
    if op == "¬":
        s = to_sympy(node.get("state"), lossless=lossless)
        if lossless and s == PH_EMPTY:
            return PH_EMPTY
        return Not(s, evaluate=False)
    if op == "↔":
        a, b = node.get("states", [None, None])
        if a == b:
            return PH_TOP if lossless else sp.S.true
        return Equivalent(
            to_sympy(a, lossless=lossless),
            to_sympy(b, lossless=lossless),
            evaluate=False,
        )

    # ---- photon algebraic ops ----
    if op == "★":
        return PhotonStar(to_sympy(node.get("state"), lossless=lossless))
    if op == "⊖":
        a, b = node.get("states", [None, None])
        return PhotonMinus(to_sympy(a, lossless=lossless),
                           to_sympy(b, lossless=lossless))
    if op == "≈":
        a, b = node.get("states", [None, None])
        return PhotonApprox(to_sympy(a, lossless=lossless),
                            to_sympy(b, lossless=lossless))
    if op == "⊂":
        a, b = node.get("states", [None, None])
        if a == b:
            return PH_TOP if lossless else sp.S.true
        return PhotonSubset(to_sympy(a, lossless=lossless),
                            to_sympy(b, lossless=lossless))

    # fallback
    return Symbol(f"PH_UNKNOWN_{op or 'NONE'}")


# -------------------------------------------------------------------------
# SymPy -> Photon
# -------------------------------------------------------------------------
def from_sympy(sexpr) -> Expr:
    """Convert SymPy expression back into Photon IR with full recursive canonical ordering."""
    # --- Literal booleans ---
    if sexpr == sp.S.true:
        return TOP
    if sexpr == sp.S.false:
        return BOTTOM

    # --- Symbolic constants ---
    if sexpr == PH_EMPTY:
        return EMPTY
    if sexpr == PH_TOP:
        return TOP
    if sexpr == PH_BOTTOM:
        return BOTTOM

    # --- Atomic symbols ---
    if isinstance(sexpr, sp.Symbol):
        name = str(sexpr)
        if name in {"PH_EMPTY", "PH_TOP", "PH_BOTTOM"}:
            return {"op": name.replace("PH_", "")}
        return name

    # --- Recursive conversion helper ---
    def _convert(expr):
        if isinstance(expr, sp.Symbol):
            return from_sympy(expr)
        if expr == sp.S.true:
            return TOP
        if expr == sp.S.false:
            return BOTTOM

        if isinstance(expr, Or):
            return {"op": "⊕", "states": [_convert(a) for a in expr.args]}
        if isinstance(expr, And):
            return {"op": "⊗", "states": [_convert(a) for a in expr.args]}
        if isinstance(expr, Not):
            return {"op": "¬", "state": _convert(expr.args[0])}
        if isinstance(expr, Equivalent):
            args = [_convert(a) for a in expr.args]
            if len(args) == 2 and args[0] == args[1]:
                return {"op": "⊤"}
            return {"op": "↔", "states": args}
        if isinstance(expr, PhotonStar):
            return {"op": "★", "state": _convert(expr.args[0])}
        if isinstance(expr, PhotonMinus):
            return {"op": "⊖", "states": [_convert(a) for a in expr.args]}
        if isinstance(expr, PhotonApprox):
            return {"op": "≈", "states": [_convert(a) for a in expr.args]}
        if isinstance(expr, PhotonSubset):
            a, b = [_convert(x) for x in expr.args]
            if a == b:
                return {"op": "⊤"}
            return {"op": "⊂", "states": [a, b]}
        return str(expr)

    # --- Deep canonical recursive sort ---
    def _canon(expr):
        """Recursively sort commutative ops for deterministic equivalence."""
        if isinstance(expr, dict):
            op = expr.get("op")

            # Canonicalize children first
            if "states" in expr:
                expr["states"] = [_canon(s) for s in expr["states"]]
            if "state" in expr:
                expr["state"] = _canon(expr["state"])

            # Sort only commutative operators
            if op in COMMUTATIVE_OPS:
                expr["states"] = sorted(expr["states"], key=lambda x: str(x))

            # For nested states: ensure each child dict is also normalized
            expr = {
                k: (_canon(v) if isinstance(v, dict) else v)
                for k, v in expr.items()
            }
        return expr

    # Convert first, then canonicalize deeply and normalize nested commutatives
    out = _canon(_convert(sexpr))

    # Ensure final pass re-sorts deeply nested commutative children
    def _deep_fix(expr):
        if isinstance(expr, dict):
            op = expr.get("op")
            if "states" in expr:
                expr["states"] = [_deep_fix(s) for s in expr["states"]]
                if op in COMMUTATIVE_OPS:
                    expr["states"] = sorted(expr["states"], key=lambda x: str(x))
            elif "state" in expr:
                expr["state"] = _deep_fix(expr["state"])
        return expr

    return _deep_fix(out)


# -------------------------------------------------------------------------
# Boolean lowering helper
# -------------------------------------------------------------------------
def lower_to_bool(sexpr):
    """Replace custom PH_* constants with True/False for boolean-only contexts."""
    return sexpr.xreplace({
        PH_TOP: sp.S.true,
        PH_EMPTY: sp.S.false,
        PH_BOTTOM: sp.S.false,
    })


__all__ = [
    "to_sympy",
    "from_sympy",
    "lower_to_bool",
    "PH_EMPTY",
    "PH_TOP",
    "PH_BOTTOM",
]