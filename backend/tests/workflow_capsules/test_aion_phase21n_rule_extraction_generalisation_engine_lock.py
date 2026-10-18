import json

from backend.modules.aion_strategy import run_rule_extraction_generalisation_engine


def test_phase21n_extracts_rules_from_prediction_memory(tmp_path):
    prediction_memory = tmp_path / "prediction_memory.json"
    rule_memory = tmp_path / "rule_memory.json"

    prediction_memory.write_text(
        json.dumps(
            {
                "prediction_model": {"A": 0.0, "B": 0.998, "C": -0.9},
                "prediction_confidence": {"A": 0.6, "B": 1.0, "C": 0.8},
            }
        ),
        encoding="utf-8",
    )

    result = run_rule_extraction_generalisation_engine(
        prediction_memory_path=prediction_memory,
        rule_memory_path=rule_memory,
    )

    assert result.engine_version == "phase21n_rule_extraction_generalisation_engine_v1"
    assert result.prediction_memory_loaded is True
    assert result.extracted_rule_count == 3
    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_rule_extraction"] is True
    assert result.evidence["uses_transfer_generalisation"] is True
    assert result.generalisation_score >= 0.66
    assert rule_memory.exists()


def test_phase21n_reward_rule_transfers_to_new_labels(tmp_path):
    prediction_memory = tmp_path / "prediction_memory.json"
    rule_memory = tmp_path / "rule_memory.json"

    prediction_memory.write_text(
        json.dumps(
            {
                "prediction_model": {"B": 0.99},
                "prediction_confidence": {"B": 1.0},
            }
        ),
        encoding="utf-8",
    )

    result = run_rule_extraction_generalisation_engine(
        prediction_memory_path=prediction_memory,
        rule_memory_path=rule_memory,
    )

    reward_rules = [r for r in result.rules if r["rule_type"] == "prefer_reward_action"]
    assert reward_rules
    trial = result.generalisation_trials[0]
    assert trial["transferred_action"] == "centre"
    assert trial["actual_reward"] == 1.0
    assert trial["success"] is True


def test_phase21n_handles_missing_prediction_memory(tmp_path):
    result = run_rule_extraction_generalisation_engine(
        prediction_memory_path=tmp_path / "missing.json",
        rule_memory_path=tmp_path / "rule_memory.json",
    )

    assert result.prediction_memory_loaded is False
    assert result.extracted_rule_count == 0
    assert result.generalisation_score == 0.0
