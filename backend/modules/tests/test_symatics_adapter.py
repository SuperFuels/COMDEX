# File: backend/modules/tests/test_symatics_adapter.py
import math
import pytest

from backend.symatics import rewriter as sym
from backend.symatics.adapter import codex_ast_to_sym, sym_to_codex_ast


# ─── Roundtrip Tests ────────────────────────────────────────────────────────────

def test_roundtrip_literal():
    node = {"op": "lit", "value": "A"}
    expr = codex_ast_to_sym(node)
    assert isinstance(expr, sym.Atom)
    assert expr.name == "A"

    back = sym_to_codex_ast(expr)
    assert back == node


def test_roundtrip_bot():
    node = {"op": "logic:⊥", "args": []}
    expr = codex_ast_to_sym(node)
    assert isinstance(expr, sym.Bot)

    back = sym_to_codex_ast(expr)
    assert back == node


def test_roundtrip_add():
    node = {
        "op": "logic:⊕",
        "args": [{"op": "lit", "value": "A"}, {"op": "lit", "value": "B"}],
    }
    expr = codex_ast_to_sym(node)
    assert isinstance(expr, sym.SymAdd)
    assert isinstance(expr.left, sym.Atom)
    assert isinstance(expr.right, sym.Atom)

    back = sym_to_codex_ast(expr)
    assert back == node


def test_roundtrip_sub():
    node = {
        "op": "logic:⊖",
        "args": [{"op": "lit", "value": "X"}, {"op": "lit", "value": "Y"}],
    }
    expr = codex_ast_to_sym(node)
    assert isinstance(expr, sym.SymSub)

    back = sym_to_codex_ast(expr)
    assert back == node


def test_roundtrip_interf():
    node = {
        "op": "interf:⋈",
        "phase": math.pi,
        "args": [{"op": "lit", "value": "P"}, {"op": "lit", "value": "Q"}],
    }
    expr = codex_ast_to_sym(node)
    assert isinstance(expr, sym.Interf)
    assert math.isclose(expr.phase, math.pi)
    assert isinstance(expr.left, sym.Atom)
    assert isinstance(expr.right, sym.Atom)

    back = sym_to_codex_ast(expr)
    assert back == node


# ─── Fallback / Unknown Handling ────────────────────────────────────────────────

def test_fallback_unknown_op():
    node = {"op": "mystery:Ω", "args": []}
    expr = codex_ast_to_sym(node)
    assert isinstance(expr, sym.Atom)
    assert expr.name == "mystery:Ω"