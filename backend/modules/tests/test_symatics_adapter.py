import math
import pytest

from backend.symatics import rewriter as sym
from backend.symatics.adapter import codex_ast_to_sym, sym_to_codex_ast


# ─── Roundtrip Tests ────────────────────────────────────────────────────────────

def test_roundtrip_literal():
    node = {"op": "lit", "value": "A"}
    expr = codex_ast_to_sym(node)

    assert isinstance(expr, sym.Var)
    assert expr.name == "A"

    back = sym_to_codex_ast(expr)
    assert back == node


def test_roundtrip_bot():
    node = {"op": "logic:⊥", "args": []}
    expr = codex_ast_to_sym(node)

    # Current adapter makes ⊥ a plain Sym("⊥")
    assert isinstance(expr, sym.Sym)
    assert expr.name in {"⊥", "logic:⊥"}

    back = sym_to_codex_ast(expr)
    assert back["op"].endswith("⊥")


def test_roundtrip_add():
    node = {
        "op": "logic:⊕",
        "args": [{"op": "lit", "value": "A"}, {"op": "lit", "value": "B"}],
    }
    expr = codex_ast_to_sym(node)

    assert isinstance(expr, sym.App)
    assert isinstance(expr.head, sym.Sym)
    assert expr.head.name in {"⊕", "logic:⊕"}
    assert all(isinstance(arg, sym.Var) for arg in expr.args)

    back = sym_to_codex_ast(expr)
    assert back["op"].endswith("⊕")


def test_roundtrip_sub():
    node = {
        "op": "logic:⊖",
        "args": [{"op": "lit", "value": "X"}, {"op": "lit", "value": "Y"}],
    }
    expr = codex_ast_to_sym(node)

    assert isinstance(expr, sym.App)
    assert isinstance(expr.head, sym.Sym)
    assert expr.head.name in {"⊖", "logic:⊖"}

    back = sym_to_codex_ast(expr)
    assert back["op"].endswith("⊖")


def test_roundtrip_interf_with_phase():
    node = {
        "op": "interf:⋈",
        "phase": math.pi,
        "args": [{"op": "lit", "value": "P"}, {"op": "lit", "value": "Q"}],
    }
    expr = codex_ast_to_sym(node)

    assert isinstance(expr, sym.App)
    assert isinstance(expr.head, sym.Sym)
    assert expr.head.name == "interf:⋈"
    assert all(isinstance(arg, sym.Var) for arg in expr.args)

    back = sym_to_codex_ast(expr)
    assert back["op"] == "interf:⋈"
    assert [a["op"] for a in back["args"]] == ["lit", "lit"]
    assert "phase" in back
    assert math.isclose(back["phase"], math.pi)


def test_roundtrip_interf_with_multiple_metadata():
    node = {
        "op": "interf:⋈",
        "phase": math.pi / 2,
        "amplitude": 0.75,
        "args": [{"op": "lit", "value": "X"}, {"op": "lit", "value": "Y"}],
    }
    expr = codex_ast_to_sym(node)

    # Ensure metadata was captured
    assert isinstance(expr, sym.App)
    assert expr.attrs is not None
    assert math.isclose(expr.attrs["phase"], math.pi / 2)
    assert math.isclose(expr.attrs["amplitude"], 0.75)

    back = sym_to_codex_ast(expr)
    assert back["op"] == "interf:⋈"
    assert "phase" in back and "amplitude" in back
    assert math.isclose(back["phase"], math.pi / 2)
    assert math.isclose(back["amplitude"], 0.75)


# ─── Fallback / Unknown Handling ────────────────────────────────────────────────

def test_fallback_unknown_op():
    node = {"op": "mystery:Ω", "args": []}
    expr = codex_ast_to_sym(node)

    # Unknown ops may become App(Sym("mystery:Ω"), [])
    if isinstance(expr, sym.Sym):
        assert expr.name == "mystery:Ω"
    else:
        assert isinstance(expr, sym.App)
        assert isinstance(expr.head, sym.Sym)
        assert expr.head.name == "mystery:Ω"
        assert expr.args == []

import random
import string

def random_metadata(n=3):
    """Generate a random dict of metadata fields (non-args, non-op)."""
    meta = {}
    for _ in range(n):
        key = "".join(random.choice(string.ascii_lowercase) for _ in range(5))
        val = random.choice([42, 3.14, "hello", True, None])
        meta[key] = val
    return meta


def test_fuzz_metadata_survives_roundtrip():
    from backend.symatics import rewriter as sym

    # Base node with a known operator and args
    node = {
        "op": "interf:⋈",
        "args": [{"op": "lit", "value": "A"}, {"op": "lit", "value": "B"}],
    }

    # Inject random metadata
    fuzz_meta = random_metadata(5)
    node.update(fuzz_meta)

    expr = codex_ast_to_sym(node)
    back = sym_to_codex_ast(expr)

    # Ensure base op and args are intact
    assert back["op"] == node["op"]
    assert [a["op"] for a in back["args"]] == ["lit", "lit"]

    # Ensure metadata survived roundtrip
    for k, v in fuzz_meta.items():
        assert back[k] == v