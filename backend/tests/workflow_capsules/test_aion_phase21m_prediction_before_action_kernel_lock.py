from backend.modules.aion_strategy import run_prediction_before_action_kernel, run_strategy_learning_kernel


def test_phase21m_prediction_before_action_reduces_prediction_error(tmp_path):
    strategy_memory = tmp_path / "strategy_memory.json"
    prediction_memory = tmp_path / "prediction_memory.json"

    run_strategy_learning_kernel(memory_path=strategy_memory, max_rounds=9)
    result = run_prediction_before_action_kernel(
        memory_path=prediction_memory,
        strategy_memory_path=strategy_memory,
        max_rounds=9,
    )

    assert result.kernel_version == "phase21m_prediction_before_action_kernel_v1"
    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_prediction_before_action"] is True
    assert result.evidence["uses_prediction_error"] is True
    assert result.evidence["uses_strategy_trust_update"] is True
    assert result.final_prediction_error <= result.baseline_prediction_error
    assert result.prediction_improved is True
    assert prediction_memory.exists()


def test_phase21m_prediction_memory_bootstraps_second_run(tmp_path):
    strategy_memory = tmp_path / "strategy_memory.json"
    prediction_memory = tmp_path / "prediction_memory.json"

    run_strategy_learning_kernel(memory_path=strategy_memory, max_rounds=9)
    first = run_prediction_before_action_kernel(
        memory_path=prediction_memory,
        strategy_memory_path=strategy_memory,
        max_rounds=9,
    )
    second = run_prediction_before_action_kernel(
        memory_path=prediction_memory,
        strategy_memory_path=strategy_memory,
        max_rounds=6,
    )

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.evidence["memory_loaded"] is True
    assert second.baseline_prediction_error <= first.baseline_prediction_error
    assert second.final_prediction_model["B"] > 0.5


def test_phase21m_attempt_records_prediction_error(tmp_path):
    prediction_memory = tmp_path / "prediction_memory.json"

    result = run_prediction_before_action_kernel(memory_path=prediction_memory, max_rounds=4)
    attempt = result.attempts[0]

    assert "predicted_reward" in attempt
    assert "actual_reward" in attempt
    assert "prediction_error" in attempt
    assert "prediction_confidence_before" in attempt
    assert "prediction_confidence_after" in attempt
    assert "observation" in attempt
