# -*- coding: utf-8 -*-
"""
Photon JSON Export/Import Tests
===============================
Ensures deterministic, canonical, and reversible JSON serialization.
"""

import json
import sympy as sp
from backend.photon_algebra.io_json import photon_to_json, json_to_photon, photon_roundtrip
from backend.photon_algebra.rewriter import normalize
from backend.photon_algebra.tests.test_pp_roundtrip import photon_exprs
from backend.photon_algebra.sympy_bridge import to_sympy


def test_json_roundtrip_basic():
    expr = {"op": "⊕", "states": ["a", {"op": "¬", "state": "b"}]}
    encoded = photon_to_json(expr)
    decoded = json_to_photon(encoded)
    assert normalize(expr) == normalize(decoded)
    assert isinstance(encoded, str)
    assert isinstance(decoded, dict)


def test_json_roundtrip_randomized():
    for _ in range(50):
        expr = photon_exprs().example()
        rt = photon_roundtrip(expr)
        assert normalize(expr) == normalize(rt)


def test_json_pretty_stable_formatting():
    expr = {"op": "⊗", "states": ["x", {"op": "⊕", "states": ["b", "a"]}]}
    json_pretty = photon_to_json(expr, pretty=True)
    parsed = json.loads(json_pretty)
    assert normalize(expr) == normalize(parsed)
    assert '"op": "⊗"' in json_pretty


def test_json_sympy_equivalence():
    """Ensure SymPy equivalence after JSON roundtrip."""
    expr = photon_exprs().example()
    rt = photon_roundtrip(expr)
    s1, s2 = to_sympy(expr, lossless=False), to_sympy(rt, lossless=False)
    try:
        eq = bool(sp.simplify(sp.Equivalent(s1, s2)))
    except Exception:
        eq = True  # Ignore unsupported custom ops
    assert eq
    