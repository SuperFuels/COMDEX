from backend.photon_algebra.photon_parse import parse
from backend.photon_algebra.rewriter import normalize
from backend.photon_algebra.renderer import render_photon


def test_parse_phi_b_unary():
    expr = parse("Φ_B a")
    assert expr == {"op": "Φ_B", "state": "a"}


def test_parse_magnetic_product():
    expr = parse("a ⊗_M b")
    assert expr == {"op": "⊗_M", "states": ["a", "b"]}


def test_parse_phi_b_over_magnetic_product():
    expr = parse("Φ_B (a ⊗_M b)")
    assert expr == {
        "op": "Φ_B",
        "state": {"op": "⊗_M", "states": ["a", "b"]},
    }


def test_normalize_phi_b_idempotent():
    expr = {"op": "Φ_B", "state": {"op": "Φ_B", "state": "a"}}
    out = normalize(expr)
    assert out == {"op": "Φ_B", "state": "a"}


def test_normalize_magnetic_product_preserves_order():
    expr = {"op": "⊗_M", "states": ["b", "a"]}
    out = normalize(expr)
    assert out == {"op": "⊗_M", "states": ["b", "a"]}


def test_render_phi_b():
    expr = {"op": "Φ_B", "state": "a"}
    assert render_photon(expr) == "Φ_Ba"


def test_render_magnetic_product():
    expr = {"op": "⊗_M", "states": ["a", "b"]}
    assert render_photon(expr) == "(a ⊗_M b)"