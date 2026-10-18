from pathlib import Path

from backend.modules.aion_learning.contracts_decision_influence import (
    DecisionInfluenceUpdate,
)
from backend.modules.aion_learning.decision_influence_runtime import (
    DecisionInfluenceRuntime,
)


def _make_runtime(tmp_path: Path) -> DecisionInfluenceRuntime:
    return DecisionInfluenceRuntime(
        weights_path=tmp_path / "decision_influence_weights.json",
        audit_jsonl_path=tmp_path / "decision_influence_audit.jsonl",
        autoload=False,
    )


def test_decision_influence_replay_restores_expected_state(tmp_path: Path):
    runtime = _make_runtime(tmp_path)

    update_1 = DecisionInfluenceUpdate(
        session_id="s1",
        turn_id="t1",
        source="test",
        reason="first update",
        updates={
            "setup_confidence_weights": {
                "field_stability": 1.25,
            },
            "llm_trust_weights": {
                "field_reasoner": 1.10,
            },
        },
        confidence=0.8,
        metadata={"case": "replay"},
    ).validate()

    res1 = runtime.apply_update(update_1, dry_run=False)
    assert res1["ok"] is True
    assert runtime.weights_version == 2

    expected_v2 = runtime.state

    update_2 = DecisionInfluenceUpdate(
        session_id="s1",
        turn_id="t2",
        source="test",
        reason="second update",
        updates={
            "setup_confidence_weights": {
                "field_drift_response": 1.40,
            },
            "event_caution_multipliers": {
                "field_anomaly": 1.55,
            },
        },
        confidence=0.7,
        metadata={"case": "replay"},
    ).validate()

    res2 = runtime.apply_update(update_2, dry_run=False)
    assert res2["ok"] is True
    assert runtime.weights_version == 3

    replayed_v2 = runtime._replay_state_to_version(2)
    assert replayed_v2 == expected_v2

    rollback_preview = runtime.rollback_to_version(2, dry_run=True)
    assert rollback_preview["ok"] is True
    assert rollback_preview["meta"]["target_version"] == 2
    assert rollback_preview["meta"]["changed"] is True