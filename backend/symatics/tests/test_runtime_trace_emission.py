"""
Runtime Trace Emission Test (v0.4)
----------------------------------
Verifies that when ctx.enable_trace=True, all runtime law validations
emit CodexTrace events through record_event().

This ensures that Tessaris' runtime validator layer is fully observable
by CodexTrace for downstream analytics and symbolic telemetry.
"""

import types
import pytest
from backend.symatics.core.validators import law_check


class DummyCtx:
    def __init__(self, validate_runtime=True, enable_trace=True):
        self.validate_runtime = validate_runtime
        self.enable_trace = enable_trace


def test_trace_emission_for_mu_collapse(monkeypatch):
    """Ensure μ collapse law triggers CodexTrace record_event call."""
    ctx = DummyCtx()
    called_events = []

    def fake_record_event(event, **fields):
        called_events.append((event, fields))

    monkeypatch.setattr(law_check, "record_event", fake_record_event)

    expr = {"op": "μ", "args": [{"op": "⊕", "args": ["ψ1", "ψ2"]}], "energy": 1.0}
    results = law_check.run_law_checks(expr, ctx)

    # Verify basic law passed
    assert "collapse_energy_equivalence" in results

    # Verify record_event was invoked at least once
    assert called_events, "record_event() was not called"
    assert any(e[0] == "law_check" for e in called_events)

    # Verify that telemetry fields include law ID and pass status
    sample = called_events[0][1]
    assert "law" in sample
    assert "passed" in sample
    assert isinstance(sample["passed"], bool)


def test_trace_emission_for_resonance_continuity(monkeypatch):
    """Ensure ⟲ resonance law also emits telemetry."""
    ctx = DummyCtx()
    called_events = []

    def fake_record_event(event, **fields):
        called_events.append(fields)

    monkeypatch.setattr(law_check, "record_event", fake_record_event)

    expr = {"op": "⟲", "freqs": [100.0, 100.1, 99.9]}
    law_check.run_law_checks(expr, ctx)

    assert called_events, "No events recorded for ⟲ resonance"
    assert any("law" in e and e["law"].startswith("resonance_") for e in called_events)

def test_trace_disabled_no_emission(monkeypatch):
    """Verify that when enable_trace=False, no CodexTrace events are recorded."""
    class DummyCtx:
        def __init__(self):
            self.validate_runtime = True
            self.enable_trace = False

    ctx = DummyCtx()
    called_events = []

    def fake_record_event(event, **fields):
        called_events.append((event, fields))

    # Monkeypatch CodexTrace emitter
    monkeypatch.setattr(law_check, "record_event", fake_record_event)

    expr = {"op": "μ", "args": [{"op": "⊕", "args": ["ψ1", "ψ2"]}], "energy": 1.0}
    law_check.run_law_checks(expr, ctx)

    # When tracing is disabled, no telemetry should be emitted
    assert called_events == [], "record_event() was unexpectedly called"