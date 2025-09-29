import pytest
from backend.modules.codex import rewrite_rules as rr


def test_double_negation_rewrites(monkeypatch):
    monkeypatch.setattr(rr, "CANONICAL_OPS", {"¬": "logic:¬"})
    tree = {"op": "¬", "args": [{"op": "¬", "args": ["A"]}]}
    out = rr.rewrite_tree(tree)
    assert out == "A"


def test_xor_self_rewrites(monkeypatch):
    monkeypatch.setattr(rr, "CANONICAL_OPS", {"⊕": "logic:⊕"})
    tree = {"op": "⊕", "args": ["X", "X"]}
    out = rr.rewrite_tree(tree)
    assert out == {"op": "logic:false"}


@pytest.mark.parametrize("op", ["∨", "∧"])
def test_idempotent_ops(monkeypatch, op):
    monkeypatch.setattr(rr, "CANONICAL_OPS", {op: f"logic:{op}"})
    tree = {"op": op, "args": ["P", "P"]}
    out = rr.rewrite_tree(tree)
    assert out == "P"


def test_canonicalization_applied(monkeypatch):
    monkeypatch.setattr(rr, "CANONICAL_OPS", {"⊕": "logic:⊕"})
    tree = {"op": "⊕", "args": ["A", "B"]}
    out = rr.rewrite_tree(tree)
    assert out["op"] == "logic:⊕"