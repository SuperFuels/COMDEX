import pytest

from backend.modules.glyphos.codexlang_translator import parse_action_expr, translate_node
from backend.modules.codex.collision_resolver import resolve_collision


def test_translate_node_resolves_logic_tensor():
    """⊗ should resolve to logic:⊗ by default priority."""
    expr = "⊗(A, B)"
    parsed = parse_action_expr(expr)
    translated = translate_node(parsed)
    assert translated["op"] == "logic:⊗"
    assert translated["args"] == ["A", "B"]


def test_translate_node_resolves_quantum_xor():
    """⊕_q should resolve to quantum:⊕ explicitly."""
    expr = "⊕_q(A, B)"
    parsed = parse_action_expr(expr)
    translated = translate_node(parsed)
    assert translated["op"] == "quantum:⊕"
    assert translated["args"] == ["A", "B"]


def test_translate_node_resolves_logic_or_quantum_collision():
    """Plain ⊕ should resolve to logic:⊕ by priority (logic first)."""
    expr = "⊕(X, Y)"
    parsed = parse_action_expr(expr)
    translated = translate_node(parsed)
    assert translated["op"] == "logic:⊕"
    assert translated["args"] == ["X", "Y"]


def test_translate_node_resolves_equivalence_collision():
    """↔ should resolve to logic:↔ by priority (logic > quantum)."""
    expr = "↔(P, Q)"
    parsed = parse_action_expr(expr)
    translated = translate_node(parsed)
    assert translated["op"] == "logic:↔"
    assert translated["args"] == ["P", "Q"]


def test_resolve_collision_with_context_hint():
    """Directly test resolver with context hint (quantum)."""
    assert resolve_collision("⊗", context="physics") == "physics:⊗"
    assert resolve_collision("⊗", context="symatics") == "symatics:⊗"
    assert resolve_collision("⊕", context="quantum") == "quantum:⊕"