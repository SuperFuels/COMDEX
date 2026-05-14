# ──────────────────────────────────────────────
#  Tessaris * Test: Aion Integration Bridge
#  Validates ψ-κ-T-Φ -> A1-A3 projection & feedback
# ──────────────────────────────────────────────
import math
import pytest
from types import SimpleNamespace
from datetime import datetime

from backend.modules.aion.aion_integration_bridge import AionIntegrationBridge


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────
class DummyFeedbackController:
    def __init__(self, target_coherence=0.92):
        self.target_coherence = target_coherence


class DummyQQC:
    def __init__(self):
        # Simulated last_summary snapshot
        self.last_summary = {
            "phi": 0.67,
            "coherence": 0.85,
            "field_signature": {
                "ψ": 2.4,
                "κ": 0.13,
                "T": 1.2,
            },
        }
        self.feedback_controller = DummyFeedbackController()


# ──────────────────────────────────────────────
#  Tests
# ──────────────────────────────────────────────
def test_projection_generates_expected_fields(monkeypatch):
    """Ensure ψκTΦ projection creates normalized A1-A3 output."""
    qqc = DummyQQC()
    bridge = AionIntegrationBridge(qqc)

    proj = bridge.project_to_aion_field()

    # check structure
    assert isinstance(proj, dict)
    assert "A1_wave" in proj
    assert "A3_awareness" in proj
    assert "coherence" in proj
    assert 0 <= proj["coherence"] <= 1
    assert abs(proj["A1_wave"]) <= 1
    assert abs(proj["A2_entropy"]) <= 1
    assert abs(proj["A3_awareness"]) <= 1
    assert isinstance(proj["timestamp"], str)
    # check gradient calculation logic
    grad_expected = round(abs(proj["A1_wave"] - proj["A2_entropy"]) + abs(proj["A3_awareness"] - proj["coherence"]), 5)
    assert math.isclose(proj["gradient"], grad_expected, abs_tol=1e-5)


def test_feedback_adjusts_target_coherence(monkeypatch):
    """Ensure gradient feedback modifies QQC feedback target within safe range."""
    qqc = DummyQQC()
    bridge = AionIntegrationBridge(qqc)
    proj = bridge.project_to_aion_field()

    # snapshot before
    original_target = qqc.feedback_controller.target_coherence
    bridge.propagate_feedback()
    new_target = qqc.feedback_controller.target_coherence

    # must stay within [0.5, 0.98]
    assert 0.5 <= new_target <= 0.98
    # feedback should cause small change (±10%)
    assert abs(new_target - original_target) < 0.1


def test_projection_handles_missing_summary(monkeypatch):
    """Bridge should not crash with empty QQC summary."""
    qqc = SimpleNamespace(last_summary={})
    qqc.feedback_controller = DummyFeedbackController()
    bridge = AionIntegrationBridge(qqc)
    result = bridge.project_to_aion_field()
    assert isinstance(result, dict)
    # result must at least have default keys
    for k in ("A1_wave", "A2_entropy", "A3_awareness"):
        assert k in result


def test_feedback_safe_on_empty_projection(monkeypatch):
    """Ensure propagate_feedback() silently skips if projection missing."""
    qqc = DummyQQC()
    bridge = AionIntegrationBridge(qqc)
    # forcibly clear projection
    bridge.last_projection = None
    # should not raise
    bridge.propagate_feedback()