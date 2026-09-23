from backend.modules.aion_survival import run_mini_survival_environment_kernel


def test_phase21p_mini_survival_environment_runs_and_survives(tmp_path):
    memory_path = tmp_path / "mini_survival_memory.json"

    result = run_mini_survival_environment_kernel(
        memory_path=memory_path,
        max_ticks=12,
        start_energy=6.0,
    )

    assert result.kernel_version == "phase21p_mini_survival_environment_kernel_v1"
    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_survival_world"] is True
    assert result.evidence["uses_prediction_before_action"] is True
    assert result.evidence["uses_policy_update"] is True
    assert result.ticks_run > 0
    assert result.survived is True
    assert result.final_energy > 0
    assert result.food_collected >= 1
    assert any(tick["action"] != "rest" for tick in result.ticks)
    assert memory_path.exists()


def test_phase21p_survival_memory_bootstraps_second_run(tmp_path):
    memory_path = tmp_path / "mini_survival_memory.json"

    first = run_mini_survival_environment_kernel(memory_path=memory_path, max_ticks=12)
    second = run_mini_survival_environment_kernel(memory_path=memory_path, max_ticks=12)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.evidence["memory_loaded"] is True
    assert second.survived is True
    assert second.survival_score >= 1.0


def test_phase21p_tick_records_prediction_and_energy(tmp_path):
    memory_path = tmp_path / "mini_survival_memory.json"

    result = run_mini_survival_environment_kernel(memory_path=memory_path, max_ticks=5)
    tick = result.ticks[0]

    assert "predicted_delta_energy" in tick
    assert "actual_delta_energy" in tick
    assert "prediction_error" in tick
    assert "energy_after" in tick
    assert "cell_type" in tick
    assert "observation" in tick
