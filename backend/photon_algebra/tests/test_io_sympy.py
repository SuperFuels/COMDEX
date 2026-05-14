# -*- coding: utf-8 -*-
"""
Tests: Photon JSON ↔ SymPy Interop
==================================
Ensures structural and logical equivalence across conversions.
"""

import json
import sympy as sp
from backend.photon_algebra.io_sympy import json_to_sympy, sympy_to_json, json_simplify_roundtrip
from backend.photon_algebra.tests.test_pp_roundtrip import photon_exprs
from backend.photon_algebra.rewriter import normalize
from backend.photon_algebra.sympy_bridge import to_sympy


def test_json_to_sympy_and_back():
    expr = photon_exprs().example()
    s_expr = json_to_sympy(expr)
    back = sympy_to_json(s_expr)
    assert normalize(back) == normalize(expr)


def test_json_simplify_roundtrip_equivalence():
    expr = photon_exprs().example()
    simplified = json_simplify_roundtrip(expr)
    s1 = to_sympy(expr, lossless=False)
    s2 = to_sympy(simplified, lossless=False)
    assert bool(sp.simplify(sp.Equivalent(s1, s2)))


def test_known_manual_case():
    expr = {"op": "⊕", "states": ["a", {"op": "⊗", "states": ["b", "a"]}]}
    s_expr = json_to_sympy(expr)
    back = sympy_to_json(s_expr)
    assert normalize(back) == {"op": "⊕", "states": ["a", {"op": "⊗", "states": ["a", "b"]}]}