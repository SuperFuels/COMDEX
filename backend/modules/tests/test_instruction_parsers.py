import pytest

from backend.modules.codex.virtual.instruction_parser import parse_codexlang
from backend.codexcore_virtual.instruction_parser import parse_codex_instructions


# ─── TREE PARSER TESTS ───────────────────────────────

def test_tree_parser_literal():
    result = parse_codexlang("⚛")
    assert result == {"op": "lit", "value": "⚛"}


def test_tree_parser_simple_chain():
    result = parse_codexlang("A -> B")
    assert result["op"].endswith("->")
    assert result["args"][0]["value"] == "A"
    assert result["args"][1]["value"] == "B"


def test_tree_parser_nested_expression():
    result = parse_codexlang("A ⊕ B -> C")
    assert result["op"].endswith("->")
    left = result["args"][0]
    assert left["op"].endswith("⊕")
    assert left["args"][0]["value"] == "A"
    assert left["args"][1]["value"] == "B"
    right = result["args"][1]
    assert right["value"] == "C"


def test_tree_parser_program_wraps():
    result = parse_codexlang("A B C")
    assert result["op"] == "program"
    assert len(result["children"]) == 3
    assert all(node["op"] == "lit" for node in result["children"])


# ─── NEW: PARENTHESIS / NESTED EXPRESSIONS ───────────────────────────────

def test_tree_parser_parentheses_group():
    result = parse_codexlang("(A ⊕ B) -> C")
    assert result["op"].endswith("->")
    left = result["args"][0]
    assert left["op"].endswith("⊕")
    assert left["args"][0]["value"] == "A"
    assert left["args"][1]["value"] == "B"
    right = result["args"][1]
    assert right["value"] == "C"


def test_tree_parser_reflect_with_inner_op():
    result = parse_codexlang("⟲(A ⊕ B)")
    assert result["op"].endswith("⟲")
    inner = result["args"][0]
    assert inner["op"].endswith("⊕")
    assert inner["args"][0]["value"] == "A"
    assert inner["args"][1]["value"] == "B"


def test_tree_parser_nested_reflect_chain():
    result = parse_codexlang("⟲((A ⊕ B) -> C)")
    assert result["op"].endswith("⟲")
    inner = result["args"][0]
    assert inner["op"].endswith("->")
    assert inner["args"][0]["op"].endswith("⊕")
    assert inner["args"][1]["value"] == "C"


# ─── FLAT PARSER TESTS ───────────────────────────────

def test_flat_parser_simple_addition():
    result = parse_codex_instructions("A ⊕ B")
    assert result[0]["opcode"].endswith("⊕")
    assert result[0]["args"] == ["A", "B"]


def test_flat_parser_chain_forward():
    result = parse_codex_instructions("X -> Y")
    assert result[0]["opcode"].endswith("->")
    assert result[0]["args"] == ["X", "Y"]


def test_flat_parser_reflect_action():
    result = parse_codex_instructions("⟲(Reflect)")
    assert result[0]["opcode"].endswith("⟲")
    assert result[0]["args"] == ["Reflect"]


def test_flat_parser_chained_segments():
    result = parse_codex_instructions("A ⊕ B -> C => ⟲(Loop)")
    ops = [r["opcode"] for r in result]
    assert any(op.endswith("⊕") for op in ops)
    assert any(op.endswith("->") for op in ops)
    assert any(op.endswith("⟲") for op in ops)