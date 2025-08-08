# backend/tests/test_physics_ops.py
import pytest

# Import the registry you wired earlier
from backend.codexcore_virtual.instruction_registry import registry


def run(symbol: str, **kwargs):
    """
    Convenience helper: calls the registry and ensures we always get a GlyphNode-like dict back.
    """
    out = registry.execute(symbol, kwargs)
    assert isinstance(out, dict), f"Expected dict, got {type(out)}"
    assert out.get("type") == "GlyphNode", f"Unexpected node type: {out}"
    return out


# ------------ Vector / Tensor calculus ------------

def test_grad():
    g = run("∇", field={"expr": "x^2 + y^2"}, coords=["x", "y"])
    assert g["op"] == "∇"
    assert g["args"][1] == ["x", "y"]


def test_div():
    d = run("∇·", vec={"expr": ["x", "y", "z"]}, coords=["x", "y", "z"])
    assert d["op"] == "∇·"


def test_curl():
    c = run("∇×", vec={"expr": ["y", "-x", "0"]}, coords=["x", "y", "z"])
    assert c["op"] == "∇×"


def test_laplacian():
    L = run("Δ", field={"expr": "x*y"}, coords=["x", "y"])
    assert L["op"] == "Δ"


def test_d_dt():
    t = run("d/dt", expr={"expr": "sin(ω*t)"}, t="t")
    # We normalize to "d/dt" in the registry
    assert t["op"] in ("d/dt", "∂/∂t")


# ------------ Linear algebra / tensor ------------

def test_dot():
    d = run("·", A={"expr": ["1", "0"]}, B={"expr": ["0", "1"]})
    assert d["op"] == "·"


def test_cross():
    x = run("×", A={"expr": ["1", "0", "0"]}, B={"expr": ["0", "1", "0"]})
    assert x["op"] == "×"


def test_tensor_product():
    t = run("⊗", A={"expr": ["a1", "a2"]}, B={"expr": ["b1", "b2"]})
    assert t["op"] == "⊗"


# ------------ ASCII aliases ------------

def test_aliases_vector_and_tensor():
    g = run("GRAD", field={"expr": "x^2"}, coords=["x"])
    assert g["op"] == "∇"

    d = run("DOT", A={"expr": ["a1", "a2"]}, B={"expr": ["b1", "b2"]})
    assert d["op"] == "·"

    t = run("TENSOR", A={"expr": ["a1", "a2"]}, B={"expr": ["b1", "b2"]})
    assert t["op"] == "⊗"