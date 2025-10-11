# -*- coding: utf-8 -*-
"""
Test Suite — Symatics Dispatcher Law Integration
────────────────────────────────────────────────────
Verifies that:
  • evaluate_symatics_expr() calls SR.check_all_laws()
  • The result includes a structured 'law_check' dict
  • The summary and violation fields behave as expected
"""

import pytest
from backend.symatics import symatics_dispatcher as SD
from backend.symatics import symatics_rulebook as SR


# ---------------------------------------------------------------------------
# Utility: simple stubs (since registry_bridge may be dynamic)
# ---------------------------------------------------------------------------

class DummyRegistryBridge:
    """Minimal fake bridge used for Symatics dispatcher testing."""
    def __init__(self):
        self.executed = []

    def has_key(self, key: str) -> bool:
        return key.startswith("symatics:")

    def resolve_and_execute(self, key: str, *args, context=None):
        op = key.split(":")[1]
        self.executed.append((op, args))
        return {
            "op": op,
            "args": list(args),
            "result": f"({op} {' '.join(map(str, args))})",
            "context": context or {},
        }


@pytest.fixture(autouse=True)
def patch_registry(monkeypatch):
    """Patch registry_bridge in dispatcher with dummy bridge."""
    bridge = DummyRegistryBridge()
    monkeypatch.setattr(SD, "registry_bridge", bridge)
    yield bridge


# ---------------------------------------------------------------------------
# Core Law Integration Tests
# ---------------------------------------------------------------------------

def test_dispatcher_includes_law_check_for_superpose():
    expr = {"op": "⊕", "args": ["ψ1", "ψ2"]}
    result = SD.evaluate_symatics_expr(expr)

    assert "law_check" in result, "Dispatcher must attach law_check block"
    law_info = result["law_check"]

    assert law_info["symbol"] == "⊕"
    assert "summary" in law_info
    assert isinstance(law_info["violations"], list)


def test_dispatcher_includes_law_check_for_measurement():
    expr = {"op": "μ", "args": ["ψ"]}
    result = SD.evaluate_symatics_expr(expr)

    assert "law_check" in result
    assert result["law_check"]["symbol"] == "μ"


def test_dispatcher_includes_law_check_for_projection():
    expr = {"op": "π", "args": [[1, 2, 3], 1]}
    result = SD.evaluate_symatics_expr(expr)

    assert "law_check" in result
    assert result["law_check"]["symbol"] == "π"


def test_dispatcher_safely_handles_unknown_operator(monkeypatch):
    """Ensure unknown ops return passthrough with no crash."""
    # simulate registry without that operator
    monkeypatch.setattr(SD.registry_bridge, "has_key", lambda k: False)

    expr = {"op": "???", "args": [1, 2]}
    result = SD.evaluate_symatics_expr(expr)

    assert result.get("note") == "unregistered op passthrough"
    assert "law_check" not in result  # skipped by design


def test_law_check_structure_and_summary_consistency():
    """SR.check_all_laws() should always return structured dict."""
    result = SR.check_all_laws("⊕", "a", "b", context={"test": True})

    assert isinstance(result, dict)
    assert "summary" in result
    assert "symbol" in result
    assert "violations" in result
    assert isinstance(result["violations"], list)