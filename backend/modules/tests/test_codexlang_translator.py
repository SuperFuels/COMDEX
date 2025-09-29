# backend/modules/tests/test_codexlang_translator.py
import pytest
from backend.modules.glyphos import codexlang_translator as clt


def test_translate_node_canonicalizes_ops(monkeypatch):
    # Stub out canonical ops just for this test
    monkeypatch.setattr(
        clt,
        "CANONICAL_OPS",
        {"⊕": "logic:⊕", "↔": "quantum:↔"}
    )

    node = {"op": "⊕", "args": ["A", {"op": "↔", "args": ["X", "Y"]}]}
    result = clt.translate_node(node)

    assert result["op"] == "logic:⊕"
    assert result["args"][1]["op"] == "quantum:↔"


@pytest.mark.parametrize("expr,expected", [
    ("A ∧ B → C", "logic:→"),   # top-level is implication
    ("¬A ∨ B", "logic:∨"),     # top-level is OR
])
def test_logic_to_tree_ops_are_canonical(expr, expected, monkeypatch):
    monkeypatch.setattr(
        clt,
        "CANONICAL_OPS",
        {"∧": "logic:∧", "∨": "logic:∨", "→": "logic:→"}
    )
    tree = clt.logic_to_tree(expr)
    tree = clt.translate_node(tree)
    assert tree["op"] == expected


def test_parse_codexlang_string_action_is_parsed_dict():
    glyph = "⟦ Logic | Test: A → ⊕(Grow, Reflect) ⟧"
    parsed = clt.parse_codexlang_string(glyph)
    assert "action" in parsed
    action = parsed["action"]

    # ✅ Now action should be parsed into a dict with canonicalized op
    assert isinstance(action, dict)
    assert action["op"] == "logic:⊕"
    assert action["args"] == ["Grow", "Reflect"]


def test_nested_action_expr_translation(monkeypatch):
    monkeypatch.setattr(
        clt,
        "CANONICAL_OPS",
        {"⊕": "logic:⊕", "↔": "quantum:↔"}
    )
    expr = "⊕(Grow, ↔(Dream, Reflect))"
    parsed = clt.parse_action_expr(expr)
    out = clt.translate_node(parsed)
    # outer op should be canonicalized
    assert out["op"] == "logic:⊕"
    # inner op should also be canonicalized
    assert out["args"][1]["op"] == "quantum:↔"


def test_invalid_codexlang_string_returns_none():
    bad = "not a codexlang string"
    parsed = clt.parse_codexlang_string(bad)
    assert parsed is None