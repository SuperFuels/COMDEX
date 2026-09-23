from backend.modules.aion_survival import run_adversarial_moving_predator_kernel


def test_phase21w_predicts_moving_predator_and_changes_action(tmp_path):
    result = run_adversarial_moving_predator_kernel(memory_path=tmp_path / "predator_memory.json")

    assert result.kernel_version == "phase21w_adversarial_moving_predator_kernel_v1"
    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_adversarial_moving_hazard"] is True
    assert result.evidence["uses_predator_future_prediction"] is True
    assert result.lookahead_changed_action is True
    assert result.shallow_first_action == "right"
    assert result.deep_first_action == "up"
    assert result.predator_intercepts_predicted_for_shallow_action >= 1
    assert result.predator_intercepts_predicted_for_deep_action == 0
    assert result.predator_avoided_before_impact is True
    assert result.predator_intercepts_actual == 0
    assert result.survived is True


def test_phase21w_reaches_goal_while_avoiding_predator(tmp_path):
    result = run_adversarial_moving_predator_kernel(memory_path=tmp_path / "predator_memory.json")

    assert result.goal_reached is True
    assert result.ticks_run > 0
    assert any(step["avoided_predator_future"] for step in result.execution_trace)


def test_phase21w_persists_predator_memory(tmp_path):
    memory_path = tmp_path / "predator_memory.json"

    first = run_adversarial_moving_predator_kernel(memory_path=memory_path)
    second = run_adversarial_moving_predator_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_predator_policy["successful_predator_avoidances"] >= 2
    assert memory_path.exists()
