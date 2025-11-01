# -*- coding: utf-8 -*-
"""
Photon Serialization & Interop Validation
========================================
Task: I5 - End-to-End Serialization Consistency

Ensures that Photon algebraic expressions can safely round-trip between
JSON -> Photon IR -> SymPy -> Simplified Photon -> JSON without semantic loss.

Primary goal:
    Guarantee stable interoperability between Photon and SymPy layers.
"""

import json
import sympy as sp
from backend.photon_algebra.sympy_bridge import to_sympy, from_sympy
from backend.photon_algebra.rewriter import normalize


# -------------------------------------------------------------------------
# Core roundtrip function
# -------------------------------------------------------------------------
def roundtrip_json_photon(expr_json: str, simplify=False):
    """
    Perform JSON ↔ Photon ↔ SymPy ↔ Photon ↔ JSON roundtrip.

    Args:
        expr_json (str): JSON-encoded Photon expression.
        simplify (bool): whether to apply SymPy simplification.
    Returns:
        dict: final Photon expression object after roundtrip.
    """
    expr = json.loads(expr_json)
    s = to_sympy(expr, lossless=True)

    if simplify:
        try:
            s = sp.simplify(s)
        except Exception:
            pass

    back = from_sympy(s)
    return back


# -------------------------------------------------------------------------
# Validation utility
# -------------------------------------------------------------------------
def validate_roundtrip(expr, simplify=False):
    """Validate that roundtrip preserves semantics."""
    expr_json = json.dumps(expr, ensure_ascii=False)
    back = roundtrip_json_photon(expr_json, simplify=simplify)
    n1, n2 = normalize(back), normalize(expr)

    if n1 != n2:
        try:
            s1 = to_sympy(expr, lossless=False)
            s2 = to_sympy(back, lossless=False)
            equivalent = bool(sp.simplify(sp.Equivalent(s1, s2)))
        except Exception:
            equivalent = False
        return equivalent
    return True


# -------------------------------------------------------------------------
# CLI self-test
# -------------------------------------------------------------------------
if __name__ == "__main__":
    sample = {"op": "⊕", "states": ["a", {"op": "¬", "state": "b"}]}
    print("Original:", json.dumps(sample, ensure_ascii=False))
    print("Roundtrip:", json.dumps(roundtrip_json_photon(json.dumps(sample)), ensure_ascii=False))