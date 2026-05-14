# -*- coding: utf-8 -*-
"""
Photon Integrated Simplifier
============================
Task: I4 - Unified simplification pipeline

Combines:
  1. Canonicalization (algebraic normalization)
  2. SymPy simplification (logic optimization)
  3. Final canonical normalization

Provides deterministic, logically equivalent simplification for Photon IR.
"""

from backend.photon_algebra.simplify_canonical import canonicalize
from backend.photon_algebra.simplify_sympy import simplify_via_sympy
from backend.photon_algebra.rewriter import normalize
from backend.photon_algebra.tests.test_pp_roundtrip import photon_exprs


def simplify(expr, mode="auto"):
    """Full simplification pipeline."""
    try:
        # Step 1: Canonical pre-pass
        canon = canonicalize(expr)

        # Step 2: SymPy-based logical simplification
        simplified = simplify_via_sympy(canon, mode=mode)

        # Step 3: Canonical post-pass (ensure stable shape)
        final = canonicalize(simplified)

        return normalize(final)
    except Exception as e:
        print(f"⚠️ simplify() fallback: {e}")
        return expr

# -----------------------------------------------------------------------------
# Integrated simplification pipeline
# -----------------------------------------------------------------------------
def simplify_pipeline(expr):
    """
    Run the full simplification pipeline:
      1. Canonicalize (deterministic normalization)
      2. Simplify via SymPy
      3. Canonicalize again to ensure stable structure
    """
    from backend.photon_algebra.simplify_sympy import simplify_via_sympy
    from backend.photon_algebra.simplify_canonical import canonicalize

    # Step 1 - canonicalize input
    canon = canonicalize(expr)

    # Step 2 - run SymPy simplification
    simplified = simplify_via_sympy(canon)

    # Step 3 - canonicalize output
    final = canonicalize(simplified)
    return final


# ---------------------------------------------------------------------
# Quick Pytest
# ---------------------------------------------------------------------
def test_simplify_pipeline_consistency():
    expr = photon_exprs().example()
    result = simplify(expr)
    assert normalize(result) == normalize(canonicalize(result))


if __name__ == "__main__":
    # Demo run
    import json
    e = photon_exprs().example()
    print("Original:", e)
    print("Simplified:", simplify(e))