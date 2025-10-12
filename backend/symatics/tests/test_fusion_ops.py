# backend/symatics/tests/test_fusion_ops.py
# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v0.5 — Quantum–Temporal Fusion Tests
# Verifies adaptive λᵢ(t) weighting & coherence behavior
# Author: Tessaris Core Systems / Codex Intelligence Group
# Version: v0.5.0 — October 2025
# ──────────────────────────────────────────────────────────────

import math
import pytest

from backend.symatics.core.fusion_ops import fuse_quantum_temporal
from backend.symatics.core.adaptive_laws import AdaptiveLawEngine


class DummyCtx:
    """Minimal runtime context used for adaptive testing."""
    def __init__(self, enable_trace=False):
        self.enable_trace = enable_trace
        self.validate_runtime = True
        self.law_weights = AdaptiveLawEngine()


@pytest.fixture
def base_exprs():
    """Generate baseline expressions for μ, ⟲, ↔."""
    mu_expr = {"op": "μ", "energy": 1.0, "phase": 0.0}
    res_expr = {"op": "⟲", "energy": 1.1, "phase": 0.2}
    ent_expr = {"op": "↔", "energy": 0.9, "phase": -0.1}
    return mu_expr, res_expr, ent_expr


def test_fusion_runs_without_error(base_exprs):
    """Ensure fusion runs and returns correct structure."""
    ctx = DummyCtx()
    mu_expr, res_expr, ent_expr = base_exprs
    res = fuse_quantum_temporal(mu_expr, res_expr, ent_expr, ctx)

    assert isinstance(res, dict)
    assert "fused_energy" in res
    assert "fused_phase" in res
    assert "coherence" in res
    assert math.isfinite(res["fused_energy"])
    assert -math.pi <= res["fused_phase"] <= math.pi


def test_fusion_respects_adaptive_weights(base_exprs):
    """Changing λᵢ weights should modify fused output."""
    ctx = DummyCtx()
    mu_expr, res_expr, ent_expr = base_exprs

    # Baseline
    res_base = fuse_quantum_temporal(mu_expr, res_expr, ent_expr, ctx)
    E_base = res_base["fused_energy"]

    # Artificially modify λ weights (simulate learning)
    ctx.law_weights.update("collapse_energy_equivalence", deviation=0.5)
    ctx.law_weights.update("resonance_continuity", deviation=-0.2)
    ctx.law_weights.update("entanglement_symmetry", deviation=0.3)

    res_mod = fuse_quantum_temporal(mu_expr, res_expr, ent_expr, ctx)
    E_mod = res_mod["fused_energy"]

    assert E_base != pytest.approx(E_mod), "Fused energy should adapt under λ drift"


def test_coherence_with_trace_enabled(base_exprs, monkeypatch):
    """Fusion emits telemetry event when trace is active."""
    events = []
    def mock_record_event(event_type, **kwargs):
        events.append((event_type, kwargs))

    monkeypatch.setattr("backend.symatics.core.fusion_ops.record_event", mock_record_event)

    ctx = DummyCtx(enable_trace=True)
    mu_expr, res_expr, ent_expr = base_exprs
    res = fuse_quantum_temporal(mu_expr, res_expr, ent_expr, ctx)

    assert res["passed"]
    assert any(ev[0] == "fusion_event" for ev in events), "Telemetry not recorded"