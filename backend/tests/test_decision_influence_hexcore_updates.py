from pathlib import Path

from backend.modules.aion_field.aion_field_control_bridge import AionFieldControlBridge
from backend.modules.aion_learning.contracts_decision_influence import (
    DecisionInfluenceUpdate,
)
from backend.modules.aion_learning.decision_influence_runtime import (
    DecisionInfluenceRuntime,
)
from backend.modules.hexcore.hexcore import HexCore


class _GoalEngineStub:
    def get_active_goals(self):
        return [{"name": "reduce_drift", "priority": 1.0, "reward": 1.0}]


def _make_runtime(tmp_path: Path) -> DecisionInfluenceRuntime:
    return DecisionInfluenceRuntime(
        weights_path=tmp_path / "decision_influence_weights.json",
        audit_jsonl_path=tmp_path / "decision_influence_audit.jsonl",
        autoload=False,
    )


def _make_hexcore_shell(tmp_path: Path) -> HexCore:
    hc = HexCore.__new__(HexCore)
    hc.id = "hex-test"
    hc.emotion_state = "neutral"
    hc.last_phi = 0.62
    hc.delta_phi = 0.24
    hc.self_awareness = 0.44
    hc.last_coherence = 0.38
    hc.last_entropy = 0.50
    hc.last_reward = 0.0
    hc.last_global_coherence = 0.41
    hc.last_goal_suggestions = ["reduce_drift", "increase_coherence"]
    hc.last_reinforcement = {"learning_rate": 0.14, "stability_factor": 0.82}
    hc.last_decision_influence_result = None
    hc.last_decision_weights_snapshot = None
    hc.goal_engine = _GoalEngineStub()
    hc.field_bridge = AionFieldControlBridge
    hc.decision_influence_runtime = _make_runtime(tmp_path)
    return hc


def test_hexcore_generated_decision_influence_update_validates_and_dry_runs(tmp_path: Path):
    hc = _make_hexcore_shell(tmp_path)

    update = hc._build_decision_influence_update(
        reward=0.18,
        coherence=0.42,
        dphi=0.31,
        goal_suggestions=["reduce_drift", "increase_coherence"],
        reinforcement={"learning_rate": 0.12, "stability_factor": 0.88},
    )

    assert isinstance(update, DecisionInfluenceUpdate)

    result = hc.decision_influence_runtime.apply_update(update, dry_run=True)

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["meta"]["changed"] is True

    applied = result["applied"]
    assert "setup_confidence_weights" in applied
    assert "stand_down_sensitivity" in applied
    assert "llm_trust_weights" in applied
    assert "event_caution_multipliers" in applied

    assert "field_stability" in applied["setup_confidence_weights"]
    assert "field_drift_response" in applied["setup_confidence_weights"]
    assert "field_instability" in applied["stand_down_sensitivity"]
    assert "field_reasoner" in applied["llm_trust_weights"]
    assert "field_anomaly" in applied["event_caution_multipliers"]