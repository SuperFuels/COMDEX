# -*- coding: utf-8 -*-
import json
import pytest
from backend.photon_algebra.photon_adapter import normalize_expr

def test_basic_distribution():
    expr = {"op": "⊗", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]}
    norm, meta = normalize_expr(expr)
    assert meta["invariants"]["no_plus_under_times"]
    assert "normalized_key" in meta
    assert isinstance(norm, dict)

def test_literal_passes_schema():
    expr = {"op": "lit", "value": "x"}
    norm, meta = normalize_expr(expr)
    assert meta["invariants"]["no_plus_under_times"]

def test_invalid_schema_rejected():
    expr = {"foo": "bar"}  # missing "op"
    with pytest.raises(Exception):
        normalize_expr(expr)