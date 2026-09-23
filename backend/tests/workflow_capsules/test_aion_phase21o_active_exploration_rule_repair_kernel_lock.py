import json

from backend.modules.aion_strategy import run_active_exploration_rule_repair_kernel


def _write_failed_rule_memory(path):
    path.write_text(
        json.dumps(
            {
                "generalisation_score": 0.666667,
                "generalisation_trials": [
                    {
                        "rule_id": "transfer_neutral_action_A",
                        "source_action": "A",
                        "success": True,
                    },
                    {
                        "rule_id": "transfer_reward_action_B",
                        "source_action": "B",
                        "success": True,
                    },
                    {
                        "rule_id": "transfer_neutral_action_C",
                        "source_action": "C",
                        "success": False,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _write_prediction_memory(path):
    path.write_text(
        json.dumps(
            {
                "prediction_model": {"A": 0.0, "B": 0.998627, "C": 0.0},
                "prediction_confidence": {"A": 0.6, "B": 1.0, "C": 0.1},
                "uses_llm_shortcut": False,
            }
        ),
        encoding="utf-8",
    )


def test_phase21o_repairs_failed_generalisation_rule(tmp_path):
    prediction_memory = tmp_path / "prediction.json"
    rule_memory = tmp_path / "rules.json"
    repair_memory = tmp_path / "repair.json"

    _write_prediction_memory(prediction_memory)
    _write_failed_rule_memory(rule_memory)

    result = run_active_exploration_rule_repair_kernel(
        prediction_memory_path=prediction_memory,
        rule_memory_path=rule_memory,
        repair_memory_path=repair_memory,
    )

    assert result.kernel_version == "phase21o_active_exploration_rule_repair_kernel_v1"
    assert result.failed_rule_count == 1
    assert result.repaired is True
    assert result.score_after_repair == 1.0
    assert result.repair_delta > 0
    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_active_exploration"] is True
    assert repair_memory.exists()


def test_phase21o_updates_prediction_memory_for_failed_action(tmp_path):
    prediction_memory = tmp_path / "prediction.json"
    rule_memory = tmp_path / "rules.json"
    repair_memory = tmp_path / "repair.json"

    _write_prediction_memory(prediction_memory)
    _write_failed_rule_memory(rule_memory)

    result = run_active_exploration_rule_repair_kernel(
        prediction_memory_path=prediction_memory,
        rule_memory_path=rule_memory,
        repair_memory_path=repair_memory,
    )

    repaired_prediction = json.loads(prediction_memory.read_text(encoding="utf-8"))

    assert repaired_prediction["prediction_model"]["C"] == -1.0
    assert repaired_prediction["prediction_confidence"]["C"] >= 0.85
    assert result.repair_actions[0]["source_action"] == "C"
    assert result.repair_actions[0]["repaired_rule_type"] == "avoid_penalty_action"


def test_phase21o_repaired_rules_include_penalty_avoidance(tmp_path):
    prediction_memory = tmp_path / "prediction.json"
    rule_memory = tmp_path / "rules.json"
    repair_memory = tmp_path / "repair.json"

    _write_prediction_memory(prediction_memory)
    _write_failed_rule_memory(rule_memory)

    result = run_active_exploration_rule_repair_kernel(
        prediction_memory_path=prediction_memory,
        rule_memory_path=rule_memory,
        repair_memory_path=repair_memory,
    )

    rule_types = {r["rule_type"] for r in result.repaired_rules}
    assert "avoid_penalty_action" in rule_types
    assert result.evidence["uses_rule_reextraction"] is True
    assert result.evidence["uses_transfer_retest"] is True
