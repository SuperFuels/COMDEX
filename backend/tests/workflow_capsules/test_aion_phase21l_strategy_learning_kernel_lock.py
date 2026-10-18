from pathlib import Path

from backend.modules.aion_strategy import run_strategy_learning_kernel


def test_phase21l_strategy_learning_kernel_improves_strategy(tmp_path):
    memory_path = tmp_path / "strategy_learning_memory.json"

    result = run_strategy_learning_kernel(memory_path=memory_path, max_rounds=9)

    assert result.kernel_version == "phase21l_strategy_learning_kernel_v1"
    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_strategy_selection"] is True
    assert result.evidence["uses_reward_feedback"] is True
    assert result.evidence["uses_trust_update"] is True
    assert result.final_score >= result.baseline_score
    assert result.improved is True
    assert memory_path.exists()


def test_phase21l_strategy_memory_bootstraps_second_run(tmp_path):
    memory_path = tmp_path / "strategy_learning_memory.json"

    first = run_strategy_learning_kernel(memory_path=memory_path, max_rounds=9)
    second = run_strategy_learning_kernel(memory_path=memory_path, max_rounds=6)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.evidence["memory_loaded"] is True
    assert second.final_strategy_trust
    assert second.evidence["uses_persistent_memory"] is True


def test_phase21l_attempts_record_strategy_action_reward(tmp_path):
    memory_path = tmp_path / "strategy_learning_memory.json"

    result = run_strategy_learning_kernel(memory_path=memory_path, max_rounds=5)
    attempt = result.attempts[0]

    assert "strategy" in attempt
    assert "action" in attempt
    assert "reward" in attempt
    assert "strategy_trust_before" in attempt
    assert "strategy_trust_after" in attempt
    assert "observation" in attempt
