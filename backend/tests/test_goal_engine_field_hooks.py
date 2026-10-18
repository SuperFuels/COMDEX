from pathlib import Path

from backend.modules.skills.goal_engine import GoalEngine


def test_ingest_field_state_suggests_expected_goals(tmp_path: Path):
    engine = GoalEngine(
        goal_file=tmp_path / "goals.json",
        resonance_enabled=False,
        autostart_resonance=False,
        broadcast_enabled=False,
    )

    suggestions = engine.ingest_field_state(
        {
            "coherence": 0.32,
            "delta_phi": 0.41,
            "entropy": 0.82,
            "self_awareness": 0.18,
            "global_coherence": 0.40,
        },
        auto_assign=False,
    )

    assert "reduce_drift" in suggestions
    assert "increase_coherence" in suggestions
    assert "reduce_entropy" in suggestions
    assert "increase_self_awareness" in suggestions
    assert "restore_global_coherence" in suggestions


def test_compute_field_reward_is_bounded_and_ordered(tmp_path: Path):
    engine = GoalEngine(
        goal_file=tmp_path / "goals.json",
        resonance_enabled=False,
        autostart_resonance=False,
        broadcast_enabled=False,
    )

    strong = engine.compute_field_reward(
        {
            "coherence": 0.95,
            "delta_phi": 0.03,
            "entropy": 0.10,
            "self_awareness": 0.90,
        }
    )
    weak = engine.compute_field_reward(
        {
            "coherence": 0.25,
            "delta_phi": 0.60,
            "entropy": 0.90,
            "self_awareness": 0.10,
        }
    )

    assert -1.0 <= strong <= 1.0
    assert -1.0 <= weak <= 1.0
    assert strong > weak


def test_apply_field_reward_updates_existing_goals(tmp_path: Path):
    engine = GoalEngine(
        goal_file=tmp_path / "goals.json",
        resonance_enabled=False,
        autostart_resonance=False,
        broadcast_enabled=False,
    )

    engine.goals = [
        {
            "name": "reduce_drift",
            "priority": 1.0,
            "reward": 1.0,
            "dependencies": [],
        }
    ]

    event = engine.apply_field_reward(
        {
            "coherence": 0.90,
            "delta_phi": 0.05,
            "entropy": 0.10,
            "self_awareness": 0.85,
        },
        goal_names=["reduce_drift"],
        persist=False,
    )

    assert event["type"] == "field_reinforcement"
    assert event["updated_goals"]
    assert engine.goals[0]["priority"] >= 1.0
    assert engine.goals[0]["reward"] >= 1.0