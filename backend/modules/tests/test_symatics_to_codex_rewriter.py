import pytest
from backend.symatics import symatics_to_codex_rewriter as scr


def test_rewrite_simple_op():
    """Symatic ⊕ should map to canonical logic:⊕."""
    tree = {"op": "⊕", "args": ["A", "B"]}
    out = scr.rewrite_symatics_to_codex(tree)
    assert out["op"] == "logic:⊕"
    assert out["args"] == ["A", "B"]


def test_rewrite_nested_ops():
    """Nested Symatics ops should be recursively rewritten."""
    tree = {
        "op": "⊕",
        "args": [
            {"op": "⋈", "args": ["X", "Y"]},
            {"op": "A"}
        ]
    }
    out = scr.rewrite_symatics_to_codex(tree)
    assert out["op"] == "logic:⊕"
    assert out["args"][0]["op"] == "interf:⋈"


def test_rewrite_non_symatic_passthrough():
    """Non-Symatics ops should remain untouched."""
    tree = {"op": "logic:∧", "args": ["P", "Q"]}
    out = scr.rewrite_symatics_to_codex(tree)
    assert out["op"] == "logic:∧"
    assert out["args"] == ["P", "Q"]


def test_is_symatic_op_checks_known_and_unknown():
    assert scr.is_symatic_op("⊕") is True
    assert scr.is_symatic_op("⋈") is True
    assert scr.is_symatic_op("logic:∧") is False
    assert scr.is_symatic_op("💀") is False


def test_list_supported_symatics_returns_mapping():
    mapping = scr.list_supported_symatics()
    assert isinstance(mapping, dict)
    assert "⊕" in mapping
    assert mapping["⊕"].startswith("logic:")