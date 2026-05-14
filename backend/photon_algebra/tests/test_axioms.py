from backend.photon_algebra import core as pa
from backend.photon_algebra.core import EMPTY  # 🔑 shared canonical empty


def test_identity():
    assert pa.identity("a") == "a"


def test_superpose():
    expr = pa.superpose("a", "b")
    assert expr["op"] == "⊕"
    assert set(expr["states"]) == {"a", "b"}


def test_entangle():
    expr = pa.entangle("a", "b")
    assert expr["op"] == "↔"
    assert "a" in expr["states"]


def test_fuse_cancel_negate():
    assert pa.fuse("a", "b")["op"] == "⊗"
    assert pa.cancel("a", "b")["op"] == "⊖"
    assert pa.negate("a")["op"] == "¬"


def test_collapse_deterministic():
    sqi = {"a": 1.0, "b": 0.0}
    expr = pa.superpose("a", "b")
    collapsed = pa.collapse(expr, sqi)
    assert collapsed == "a"


def test_projection_and_boolean():
    sqi = {"a": 0.7}
    assert pa.project("a", sqi)["score"] == 0.7
    assert pa.to_boolean("a", sqi, threshold=0.5) == 1
    assert pa.to_boolean("a", sqi, threshold=0.8) == 0


def test_rewrite_flatten():
    nested = pa.superpose("a", pa.superpose("b", "c"))
    flat = pa.rewrite(nested)
    assert set(flat["states"]) == {"a", "b", "c"}


def test_empty_constant():
    """Ensure EMPTY is always canonical ∅ dict."""
    # Canonical EMPTY should always be exactly this dict
    assert EMPTY == {"op": "∅"}
    # It should never gain unwanted "states" or mutate
    assert isinstance(EMPTY, dict)
    assert EMPTY.get("op") == "∅"
    assert "states" not in EMPTY