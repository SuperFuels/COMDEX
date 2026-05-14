import pytest
from backend.symatics import symatics_dispatcher as sd


def test_superpose_delegates_to_registry():
    """⊕ should resolve via registry, returning symatics superpose result."""
    expr = {"op": "⊕", "args": ["A", "B"]}
    result = sd.evaluate_symatics_expr(expr)

    # Should produce a structured symatics result
    assert result["result"] == "(A ⊕ B)"
    assert set(result["state"]) == {"A", "B"}


def test_measure_returns_collapse():
    expr = {"op": "μ", "args": ["Ψ"]}
    result = sd.evaluate_symatics_expr(expr)
    assert "result" in result
    assert result["op"] == "μ"


def test_entangle_combine():
    expr = {"op": "↔", "args": ["X", "Y"]}
    result = sd.evaluate_symatics_expr(expr)
    assert result["op"] == "↔"
    assert set(result["state"]) == {"X", "Y"}


def test_invalid_operator_falls_back_stub():
    expr = {"op": "??", "args": []}
    result = sd.evaluate_symatics_expr(expr)
    # RegistryBridge stub should mark it as unhandled
    assert result.get("unhandled_op") == "symatics:??"