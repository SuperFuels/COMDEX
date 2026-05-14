# -*- coding: utf-8 -*-
"""
Photon Simplification via SymPy
===============================
Task: I2.2 - SymPy-based simplifier using the Photon↔SymPy bridge.

Performs symbolic simplification of Photon expressions by round-tripping
through SymPy (using simplify(), to_cnf(), to_dnf(), etc.) while preserving
logical equivalence.

Usage:
    simplified = simplify_via_sympy(expr, mode="auto")

Modes:
    - "auto"   -> sp.simplify()
    - "cnf"    -> convert to conjunctive normal form
    - "dnf"    -> convert to disjunctive normal form
    - "sat"    -> reduce tautologies / contradictions
"""

import sympy as sp

from backend.photon_algebra.sympy_bridge import (
    to_sympy,
    from_sympy,
    PhotonStar,
    PhotonMinus,
    PhotonApprox,
    PhotonSubset,
)
from backend.photon_algebra.tests.test_pp_roundtrip import photon_exprs
from backend.photon_algebra.rewriter import normalize
from backend.photon_algebra.simplify_canonical import canonicalize


# -------------------------------------------------------------------------
# Simplify core
# -------------------------------------------------------------------------
def simplify_via_sympy(expr, mode: str = "auto"):
    """Simplify a Photon expression via SymPy, preserving logical meaning."""
    try:
        s = to_sympy(expr, lossless=False)

        # Skip simplify for expressions containing custom photon ops
        if any(isinstance(a, (PhotonStar, PhotonMinus, PhotonApprox, PhotonSubset))
               for a in s.atoms(sp.Function)):
            return canonicalize(normalize(expr))

        if mode == "cnf":
            simp = sp.to_cnf(s, simplify=True)
        elif mode == "dnf":
            simp = sp.to_dnf(s, simplify=True)
        elif mode == "sat":
            simp = sp.simplify_logic(s, form="cnf")
        else:
            simp = sp.simplify_logic(s, form="dnf")

        back = from_sympy(simp)
        back = normalize(back)
        back = canonicalize(back)
        return back

    except Exception as e:
        print(f"⚠️  Skipping complex simplify: {e}")
        return canonicalize(normalize(expr))


# -------------------------------------------------------------------------
# Roundtrip self-test (pytest)
# -------------------------------------------------------------------------
def test_simplify_photon_roundtrip():
    """Property test - simplified form should remain logically equivalent."""
    expr = photon_exprs().example()
    simplified = simplify_via_sympy(expr)

    n1, n2 = normalize(expr), normalize(simplified)
    if n1 == n2:
        assert True
        return

    s1 = to_sympy(n1, lossless=False)
    s2 = to_sympy(n2, lossless=False)

    try:
        equivalent = bool(sp.simplify(sp.Equivalent(s1, s2)))
    except Exception:
        equivalent = False

    if not equivalent:
        print("\n❌ Non-equivalent simplify case:")
        print("Original (normalized):", n1)
        print("Simplified (normalized):", n2)
        print("SymPy original:", s1)
        print("SymPy simplified:", s2)

    assert equivalent