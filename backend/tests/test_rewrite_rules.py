import pytest
from backend.symatics import rewrite_rules as rr

def test_idempotence_rule():
    expr = {"op": "⊕", "args": ["x", "x"], "state": ["x", "x"]}
    simplified = rr.normalize(expr)
    assert simplified == "x"

def test_commutativity_rule():
    expr = {"op": "⊕", "args": ["y", "x"], "state": ["y", "x"]}
    simplified = rr.normalize(expr)
    assert simplified["args"] == ["x", "y"]

def test_associativity_rule():
    expr = {
        "op": "⊕",
        "args": [
            {"op": "⊕", "args": ["a", "b"], "state": ["a", "b"]},
            "c",
        ],
    }
    simplified = rr.normalize(expr)
    assert simplified["args"] == ["a", "b", "c"]

def test_distributivity_rule():
    expr = {
        "op": "⊕",
        "args": [
            "a",
            {"op": "↔", "args": ["b", "c"]},
        ],
    }
    simplified = rr.normalize(expr)
    assert simplified["op"] == "↔"
    assert simplified["args"][0]["args"] == ["a", "b"]
    assert simplified["args"][1]["args"] == ["a", "c"]

def test_identity_rule():
    expr = {"op": "⊕", "args": ["x", "∅"]}
    simplified = rr.normalize(expr)
    assert simplified == "x"

def test_constant_folding_rule():
    # Arithmetic folding should work:
    expr = {"op": "+", "args": ["2", "3"]}
    simplified = rr.normalize(expr)
    assert simplified == "5"

    # And ⊕ must NOT fold numerically:
    expr2 = {"op": "⊕", "args": ["2", "3"]}
    simplified2 = rr.normalize(expr2)
    assert isinstance(simplified2, dict) and simplified2.get("op") == "⊕"