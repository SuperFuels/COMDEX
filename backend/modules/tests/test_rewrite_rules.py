# backend/modules/tests/test_rewrite_rules.py
import pytest
from backend.modules.codex import rewrite_rules as rr


def test_double_negation_rewrites(monkeypatch):
    monkeypatch.setattr(rr, "CANONICAL_OPS", {"¬": "logic:¬"})
    tree = {"op": "¬", "args": [{"op": "¬", "args": [{"op": "lit", "value": "A"}]}]}
    out = rr.rewrite_tree(tree)
    # Expect just literal A
    assert out == {"op": "lit", "value": "A"}


def test_xor_self_rewrites(monkeypatch):
    monkeypatch.setattr(rr, "CANONICAL_OPS", {"⊕": "logic:⊕"})
    tree = {
        "op": "⊕",
        "args": [
            {"op": "lit", "value": "X"},
            {"op": "lit", "value": "X"},
        ],
    }
    out = rr.rewrite_tree(tree)
    # Expect canonical false op (args always normalized as list)
    assert out == {"op": "logic:false", "args": []}


@pytest.mark.parametrize("op", ["∨", "∧"])
def test_idempotent_ops(monkeypatch, op):
    monkeypatch.setattr(rr, "CANONICAL_OPS", {op: f"logic:{op}"})
    tree = {
        "op": op,
        "args": [
            {"op": "lit", "value": "P"},
            {"op": "lit", "value": "P"},
        ],
    }
    out = rr.rewrite_tree(tree)
    # Expect just literal P
    assert out == {"op": "lit", "value": "P"}


def test_canonicalization_applied(monkeypatch):
    monkeypatch.setattr(rr, "CANONICAL_OPS", {"⊕": "logic:⊕"})
    tree = {
        "op": "⊕",
        "args": [
            {"op": "lit", "value": "A"},
            {"op": "lit", "value": "B"},
        ],
    }
    out = rr.rewrite_tree(tree)
    # Operator should have been canonicalized
    assert out["op"] == "logic:⊕"