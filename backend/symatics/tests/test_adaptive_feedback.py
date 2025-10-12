# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v0.5 — Adaptive Feedback Verification
# Tests for λᵢ(t) drift correction and CodexTrace telemetry
# Author: Tessaris Core Systems / Codex Intelligence Group
# ──────────────────────────────────────────────────────────────

import pytest

from backend.symatics.core.adaptive_laws import AdaptiveLawEngine

# Dummy CodexTrace stub
events = []
def mock_record_event(event_type, **kwargs):
    events.append((event_type, kwargs))


# ──────────────────────────────────────────────────────────────
# Dummy Context for adaptive testing
# ──────────────────────────────────────────────────────────────
class DummyCtx:
    def __init__(self, enable_trace=False):
        self.law_weights = AdaptiveLawEngine()
        self.enable_trace = enable_trace


# ──────────────────────────────────────────────────────────────
# Test 1 — Adaptive weight reduction with positive deviation
# ──────────────────────────────────────────────────────────────
def test_weight_reduction_on_deviation(monkeypatch):
    """λᵢ(t) decreases proportionally to deviation drift."""
    ctx = DummyCtx()
    ctx.law_weights.weights = {"collapse_energy_equivalence": 1.0}
    ctx.law_weights.alpha = 0.5

    results = {"collapse_energy_equivalence": {"deviation": 0.2}}
    ctx.law_weights.update("collapse_energy_equivalence", deviation=0.2)

    updated = ctx.law_weights.weights["collapse_energy_equivalence"]
    assert 0 < updated < 1.0, f"Expected weight to reduce, got {updated}"


# ──────────────────────────────────────────────────────────────
# Test 2 — Stability across repeated updates
# ──────────────────────────────────────────────────────────────
def test_stability_under_iterative_drift():
    """λᵢ(t) stabilizes asymptotically under repeated drift inputs."""
    ctx = DummyCtx()
    ctx.law_weights.weights = {"resonance_continuity": 1.0}
    ctx.law_weights.alpha = 0.3

    for _ in range(5):
        ctx.law_weights.update("resonance_continuity", deviation=0.1)

    final_weight = ctx.law_weights.weights["resonance_continuity"]
    assert 0.5 < final_weight < 1.0, f"Expected stable range, got {final_weight}"


# ──────────────────────────────────────────────────────────────
# Test 3 — CodexTrace event emission
# ──────────────────────────────────────────────────────────────
def test_codextrace_event_emission(monkeypatch):
    """Trace-enabled adaptive update emits telemetry event."""
    monkeypatch.setattr("backend.symatics.core.adaptive_laws.record_event", mock_record_event)
    events.clear()

    ctx = DummyCtx(enable_trace=True)
    ctx.law_weights.weights = {"entanglement_symmetry": 1.0}
    ctx.law_weights.alpha = 0.4

    ctx.law_weights.update("entanglement_symmetry", deviation=0.25)

    assert any(ev[0] == "law_weight_update" for ev in events), "No telemetry event recorded"
    event = next(ev for ev in events if ev[0] == "law_weight_update")
    assert "law_id" in event[1] and "new_weight" in event[1], "Missing expected event fields"


# ──────────────────────────────────────────────────────────────
# Test 4 — Non-negative weight floor
# ──────────────────────────────────────────────────────────────
def test_weight_floor():
    """Adaptive weights never go negative under high drift."""
    ctx = DummyCtx()
    ctx.law_weights.weights = {"collapse_energy_equivalence": 1.0}
    ctx.law_weights.alpha = 1.5  # intentionally aggressive

    ctx.law_weights.update("collapse_energy_equivalence", deviation=2.0)
    w = ctx.law_weights.weights["collapse_energy_equivalence"]
    assert w >= 0.0, f"Expected weight floor at 0, got {w}"


# ──────────────────────────────────────────────────────────────
# Test 5 — Multiple laws evolve independently
# ──────────────────────────────────────────────────────────────
def test_independent_evolution():
    """Each λᵢ evolves independently based on its own deviation."""
    ctx = DummyCtx()
    ctx.law_weights.weights = {
        "collapse_energy_equivalence": 1.0,
        "resonance_continuity": 1.0,
    }
    ctx.law_weights.alpha = 0.4

    ctx.law_weights.update("collapse_energy_equivalence", deviation=0.1)
    ctx.law_weights.update("resonance_continuity", deviation=0.4)

    w1 = ctx.law_weights.weights["collapse_energy_equivalence"]
    w2 = ctx.law_weights.weights["resonance_continuity"]
    assert w1 > w2, "Weights did not evolve independently as expected"


# ──────────────────────────────────────────────────────────────
# End of Tests
# ──────────────────────────────────────────────────────────────