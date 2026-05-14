# 📁 backend/tests/test_symatics_dispatcher.py
import pytest
from backend.symatics.symatics_dispatcher import (
    evaluate_symatics_expr,
    is_symatics_operator,
)
from backend.modules.codex.logic_tree import LogicGlyph

def make_glyph(op, args=None):
    return LogicGlyph(name=op, logic=op, operator=op, args=args or [])

def test_superposition_operator():
    g = make_glyph("⊕", ["a", "b"])
    result = evaluate_symatics_expr(g, context={})
    assert result["op"] == "⊕"
    assert result["args"] == ["a", "b"]
    assert result["result"] == "(a ⊕ b)"

def test_measurement_operator():
    g = make_glyph("μ", ["x"])
    result = evaluate_symatics_expr(g, context={})
    assert result["op"] == "μ"
    assert result["args"] == ["x"]
    assert "measurement" in result["result"]

def test_equivalence_operator():
    g = make_glyph("↔", ["p", "q"])
    result = evaluate_symatics_expr(g, context={})
    assert result["op"] == "↔"
    assert result["args"] == ["p", "q"]
    assert "↔" in result["result"]

def test_is_symatics_operator():
    assert is_symatics_operator("⊕")
    assert is_symatics_operator("μ")
    assert not is_symatics_operator("foo")