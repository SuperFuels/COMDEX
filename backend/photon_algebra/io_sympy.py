# -*- coding: utf-8 -*-
"""
Photon JSON ↔ SymPy Interop (Fully Structural, Non-Evaluating, Strict)
======================================================================
Ensures exact structural fidelity - no collapsing, no simplification.
"""

import sympy as sp
from backend.photon_algebra.simplify_canonical import canonicalize
from backend.photon_algebra.sympy_bridge import from_sympy


# -------------------------------------------------------------------------
# Non-evaluating symbolic function base
# -------------------------------------------------------------------------
class _PhotonBase(sp.Function):
    """Base for Photon symbolic ops (structural only)."""
    is_commutative = False
    is_associative = False
    is_Boolean = False
    nargs = None
    _is_photon_wrapper = True  # sentinel marker

    @classmethod
    def eval(cls, *args):
        # Disable SymPy evaluation entirely
        return None

    def doit(self, **hints):
        return self

    def simplify(self, **kwargs):
        return self

    def __eq__(self, other):
        # Disable logical equality collapsing (↔ simplification)
        if isinstance(other, _PhotonBase):
            return self is other
        return False


class PhotonLiteral(_PhotonBase):
    nargs = 1


class PhotonOr(_PhotonBase):
    """Explicit OR node - always preserved."""
    @classmethod
    def eval(cls, *args): return None
    def __new__(cls, *args, **kwargs):
        obj = sp.Basic.__new__(cls, *args, **kwargs)
        obj._args = tuple(args)
        obj._is_photon_wrapper = True
        return obj


class PhotonAnd(_PhotonBase):
    """Explicit AND node - always preserved."""
    @classmethod
    def eval(cls, *args): return None
    def __new__(cls, *args, **kwargs):
        obj = sp.Basic.__new__(cls, *args, **kwargs)
        obj._args = tuple(args)
        obj._is_photon_wrapper = True
        return obj


class PhotonEqv(_PhotonBase):
    nargs = 2
    is_commutative = False
    is_associative = False

    @classmethod
    def eval(cls, a, b):
        # Prevent simplification (a ↔ a) -> ⊤
        return None

    def __eq__(self, other):  # disable equality collapse
        return id(self) == id(other)

    def simplify(self, **kwargs):
        return self


class PhotonSubset(_PhotonBase): nargs = 2
class PhotonApprox(_PhotonBase): nargs = 2
class PhotonMinus(_PhotonBase): nargs = 2
class PhotonStar(_PhotonBase): nargs = 1


# -------------------------------------------------------------------------
# JSON -> SymPy
# -------------------------------------------------------------------------
def json_to_sympy(expr):
    """Convert Photon JSON IR -> SymPy structurally."""
    if isinstance(expr, str):
        return PhotonLiteral(sp.Symbol(expr))
    if not isinstance(expr, dict):
        return expr

    op = expr.get("op")

    if op == "⊕":
        return PhotonOr(*[json_to_sympy(s) for s in expr.get("states", [])])
    if op == "⊗":
        return PhotonAnd(*[json_to_sympy(s) for s in expr.get("states", [])])
    if op == "¬":
        return sp.Function("PhotonNot")(json_to_sympy(expr["state"]))
    if op == "↔":
        a, b = expr["states"]
        return PhotonEqv(json_to_sympy(a), json_to_sympy(b))
    if op == "⊂":
        a, b = expr["states"]
        return PhotonSubset(json_to_sympy(a), json_to_sympy(b))
    if op == "≈":
        a, b = expr["states"]
        return PhotonApprox(json_to_sympy(a), json_to_sympy(b))
    if op == "⊖":
        a, b = expr["states"]
        return PhotonMinus(json_to_sympy(a), json_to_sympy(b))
    if op == "★":
        return PhotonStar(json_to_sympy(expr["state"]))
    if op == "∅":
        return sp.Symbol("PH_EMPTY")
    if op == "⊤":
        return sp.Symbol("PH_TOP")
    if op == "⊥":
        return sp.Symbol("PH_BOTTOM")

    return sp.Symbol(f"PH_UNKNOWN_{op}")


# -------------------------------------------------------------------------
# SymPy -> JSON
# -------------------------------------------------------------------------
def sympy_to_json(sexpr):
    """Convert SymPy -> Photon JSON structurally."""
    if isinstance(sexpr, PhotonLiteral):
        (inner,) = sexpr.args
        return sympy_to_json(inner)

    if isinstance(sexpr, PhotonOr):
        states = [sympy_to_json(a) for a in sexpr.args]
        # Preserve structure even for single-child ORs
        if len(states) == 1 and isinstance(states[0], str):
            return {"op": "⊕", "states": states}
        return {"op": "⊕", "states": states}

    if isinstance(sexpr, PhotonAnd):
        states = [sympy_to_json(a) for a in sexpr.args]
        if len(states) == 1 and isinstance(states[0], str):
            return {"op": "⊗", "states": states}
        return {"op": "⊗", "states": states}

    if isinstance(sexpr, PhotonEqv):
        a, b = sexpr.args
        return {"op": "↔", "states": [sympy_to_json(a), sympy_to_json(b)]}

    if sexpr.func.__name__ == "PhotonNot":
        return {"op": "¬", "state": sympy_to_json(sexpr.args[0])}

    if isinstance(sexpr, PhotonSubset):
        a, b = sexpr.args
        return {"op": "⊂", "states": [sympy_to_json(a), sympy_to_json(b)]}

    if isinstance(sexpr, PhotonApprox):
        a, b = sexpr.args
        return {"op": "≈", "states": [sympy_to_json(a), sympy_to_json(b)]}

    if isinstance(sexpr, PhotonMinus):
        a, b = sexpr.args
        return {"op": "⊖", "states": [sympy_to_json(a), sympy_to_json(b)]}

    if isinstance(sexpr, PhotonStar):
        (a,) = sexpr.args
        return {"op": "★", "state": sympy_to_json(a)}

    if isinstance(sexpr, sp.Symbol):
        name = str(sexpr)
        if name == "PH_EMPTY":
            return {"op": "∅"}
        if name == "PH_TOP":
            return {"op": "⊤"}
        if name == "PH_BOTTOM":
            return {"op": "⊥"}
        return name

    if sexpr == sp.true:
        return {"op": "⊤"}
    if sexpr == sp.false:
        return {"op": "∅"}

    try:
        return canonicalize(from_sympy(sexpr))
    except Exception:
        return {
            "op": str(sexpr.func.__name__),
            "args": [sympy_to_json(a) for a in getattr(sexpr, "args", [])],
        }


# -------------------------------------------------------------------------
# Roundtrip helper
# -------------------------------------------------------------------------
def json_simplify_roundtrip(expr):
    s = json_to_sympy(expr)
    back = sympy_to_json(s)
    return back


# -------------------------------------------------------------------------
# DEBUG DIAGNOSTICS (TEMPORARY)
# -------------------------------------------------------------------------
import sys
def _debug_trace(expr, label):
    """Prints short diagnostic structure for debugging test collapse."""
    try:
        import json
        js = json.dumps(expr, ensure_ascii=False, indent=2)
    except Exception:
        js = str(expr)
    sys.stderr.write(f"\n[DEBUG {label}] {type(expr).__name__}:\n{js}\n")


# Wrap for debugging
_orig_json_to_sympy = json_to_sympy
_orig_sympy_to_json = sympy_to_json

def json_to_sympy(expr):
    res = _orig_json_to_sympy(expr)
    if isinstance(expr, dict) and expr.get("op") in {"⊕", "↔"}:
        _debug_trace(expr, "INPUT JSON")
        _debug_trace(res, "-> SYMPY STRUCTURE")
    return res

def sympy_to_json(sexpr):
    res = _orig_sympy_to_json(sexpr)
    if isinstance(sexpr, (_PhotonBase, sp.Function, sp.Symbol)):
        _debug_trace(sexpr, "<- FROM SYMPY")
        _debug_trace(res, "OUTPUT JSON")
    return res