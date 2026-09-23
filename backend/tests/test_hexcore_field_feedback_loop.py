from pathlib import Path

from backend.modules.aion_field.aion_field_control_bridge import AionFieldControlBridge
from backend.modules.aion_learning.decision_influence_runtime import (
    DecisionInfluenceRuntime,
)
from backend.modules.hexcore.hexcore import HexCore


class _GoalEngineStub:
    def __init__(self):
        self._active = []

    def get_active_goals(self):
        return list(self._active)

    def ingest_field_state(self, telemetry, auto_assign=False):
        goals = []
        if abs(float(telemetry.get("delta_phi", 0.0))) > 0.2:
            goals.append("reduce_drift")
        if float(telemetry.get("coherence", 0.5)) < 0.5:
            goals.append("increase_coherence")
        self._active = [{"name": g, "priority": 1.0, "reward": 1.0} for g in goals]
        return goals

    def compute_field_reward(self, telemetry):
        coherence = float(telemetry.get("coherence", 0.5))
        drift = abs(float(telemetry.get("delta_phi", 0.0)))
        return round(coherence - drift, 4)


class _ReinforcementStub:
    def __init__(self):
        self.last = None

    def update_parameters(self, learning_rate=None, stability_factor=None, drift_factor=None):
        self.last = {
            "learning_rate": round(0.1 + (float(stability_factor or 1.0) * 0.05), 3),
            "stability_factor": round(max(0.5, 1.0 - float(drift_factor or 0.0)), 3),
        }
        return dict(self.last)


def _make_runtime(tmp_path: Path) -> DecisionInfluenceRuntime:
    return DecisionInfluenceRuntime(
        weights_path=tmp_path / "decision_influence_weights.json",
        audit_jsonl_path=tmp_path / "decision_influence_audit.jsonl",
        autoload=False,
    )


def _make_hexcore_shell(tmp_path: Path) -> HexCore:
    hc = HexCore.__new__(HexCore)
    hc.id = "hex-loop"
    hc.emotion_state = "neutral"
    hc.last_phi = 0.55
    hc.delta_phi = 0.28
    hc.self_awareness = 0.40
    hc.last_coherence = 0.36
    hc.last_entropy = 0.52
    hc.last_reward = 0.0
    hc.last_global_coherence = 0.43
    hc.last_field_control = None
    hc.last_goal_suggestions = []
    hc.last_reinforcement = {}
    hc.last_decision_influence_result = None
    hc.last_decision_weights_snapshot = None
    hc.goal_engine = _GoalEngineStub()
    hc.reinforcement_engine = _ReinforcementStub()
    hc.decision_influence_runtime = _make_runtime(tmp_path)
    hc.field_bridge = AionFieldControlBridge
    return hc


def test_hexcore_field_feedback_loop_updates_control_bias(tmp_path: Path):
    hc = _make_hexcore_shell(tmp_path)

    # baseline control before any learned decision-influence state exists
    baseline_state = hc._build_aion_state()
    baseline_control = hc._map_field_control(baseline_state)

    goal_feedback = hc._ingest_field_telemetry(
        coherence=0.34,
        dphi=0.29,
        phi=0.57,
        s_self=0.30,
    )

    assert "reduce_drift" in goal_feedback["goal_suggestions"]
    assert "increase_coherence" in goal_feedback["goal_suggestions"]
    assert isinstance(goal_feedback["reward"], float)

    reinforcement = hc._apply_reward_to_reinforcement(
        coherence=0.34,
        dphi=0.29,
        reward=goal_feedback["reward"],
    )
    assert "learning_rate" in reinforcement
    assert "stability_factor" in reinforcement

    update = hc._build_decision_influence_update(
        reward=goal_feedback["reward"],
        coherence=0.34,
        dphi=0.29,
        goal_suggestions=goal_feedback["goal_suggestions"],
        reinforcement=reinforcement,
    )
    assert update is not None

    apply_result = hc.decision_influence_runtime.apply_update(update, dry_run=False)
    assert apply_result["ok"] is True
    assert apply_result["meta"]["changed"] is True

    hc.last_decision_weights_snapshot = hc.decision_influence_runtime.show_state()
    hc.last_reinforcement = reinforcement
    hc.last_reward = goal_feedback["reward"]
    hc.last_goal_suggestions = goal_feedback["goal_suggestions"]

    adapted_state = hc._build_aion_state()
    adapted_control = hc._map_field_control(adapted_state)

    # learned weights should now be present in the state driving control
    bias = adapted_state["decision_influence_bias"]
    assert bias["field_stability"] != 1.0 or bias["field_drift_response"] != 1.0

    # control should adapt after decision-influence update is applied
    assert adapted_control != baseline_control

    # drift-heavy path should still prefer stabilization
    assert adapted_control["control_priority"] in {"stabilize", "maintain"}
    assert 0.0 <= adapted_control["symbolic_temperature"] <= 1.0
    assert 0.0 <= adapted_control["resonance_gain"] <= 1.0