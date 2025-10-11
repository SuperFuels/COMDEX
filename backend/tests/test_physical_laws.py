# 📘 backend/tests/test_physical_laws.py
import os
import json
import pytest

from backend.symatics import symatics_rulebook as SR
from backend.symatics import symatics_dispatcher as dispatcher
from backend.modules.codex.codex_trace import CodexTrace

LEDGER_PATH = "docs/rfc/theorem_ledger.jsonl"


@pytest.fixture(autouse=True)
def clean_ledger(tmp_path):
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    if os.path.exists(LEDGER_PATH):
        os.remove(LEDGER_PATH)
    yield
    if os.path.exists(LEDGER_PATH):
        os.remove(LEDGER_PATH)


def read_ledger():
    if not os.path.exists(LEDGER_PATH):
        return []
    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_resonance_and_collapse_laws_emit_to_ledger():
    """Ensure ⟲ and μ operators emit law_check theorem entries."""
    ctx = {"container_id": "unit-test-container", "ghx_id": "ghx-999"}

    dispatcher.evaluate_symatics_expr({"op": "⟲", "args": ["ψ1", "ψ2"]}, context=ctx)
    dispatcher.evaluate_symatics_expr({"op": "μ", "args": ["ψ1"]}, context=ctx)

    ledger = read_ledger()
    assert len(ledger) >= 2, "Expected at least two theorem entries in ledger"

    ops = [entry["operator"] for entry in ledger]
    assert "⟲" in ops, "Resonance ⟲ should have a ledger entry"
    assert "μ" in ops, "Collapse μ should have a ledger entry"

    for entry in ledger:
        assert entry["type"] == "theorem"
        assert entry["engine"] == "symatics"
        assert "summary" in entry
        assert "violations" in entry


def test_trace_reflects_theorem_entries():
    """Ensure CodexTrace contains theorem entries for ⟲ and μ."""
    trace = CodexTrace()
    trace.clear()
    ctx = {"container_id": "trace-test", "ghx_id": "ghx-123"}

    dispatcher.evaluate_symatics_expr({"op": "⟲", "args": ["ψA", "ψB"]}, context=ctx)
    dispatcher.evaluate_symatics_expr({"op": "μ", "args": ["ψA"]}, context=ctx)

    traces = trace.get_trace()
    theorem_events = [t for t in traces if t.get("action") == "law_check"]

    assert any(t.get("operator") == "⟲" for t in theorem_events)
    assert any(t.get("operator") == "μ" for t in theorem_events)
    assert all(t["engine"] == "symatics" for t in theorem_events)