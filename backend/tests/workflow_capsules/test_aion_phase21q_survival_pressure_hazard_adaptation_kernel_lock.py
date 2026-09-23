from backend.modules.aion_survival import run_survival_pressure_hazard_adaptation_kernel


def test_phase21q_hazard_adaptation_learns_after_hazard(tmp_path):
    memory_path = tmp_path / "hazard_memory.json"

    first = run_survival_pressure_hazard_adaptation_kernel(memory_path=memory_path, max_ticks=10)
    second = run_survival_pressure_hazard_adaptation_kernel(memory_path=memory_path, max_ticks=10)

    assert first.kernel_version == "phase21q_survival_pressure_hazard_adaptation_kernel_v1"
    assert first.evidence["uses_llm_shortcut"] is False
    assert first.evidence["uses_survival_pressure"] is True
    assert first.evidence["uses_hazard_memory"] is True
    assert first.hazards_hit >= 1
    assert "1,0" in first.final_policy["known_hazards"]

    assert second.hazard_memory_loaded is True
    assert second.hazards_hit <= first.hazards_hit
    assert second.adapted is True
    assert memory_path.exists()


def test_phase21q_records_hazard_adaptation_ticks(tmp_path):
    memory_path = tmp_path / "hazard_memory.json"

    result = run_survival_pressure_hazard_adaptation_kernel(memory_path=memory_path, max_ticks=5)
    tick = result.ticks[0]

    assert "predicted_delta_energy" in tick
    assert "actual_delta_energy" in tick
    assert "prediction_error" in tick
    assert "adapted" in tick
    assert "observation" in tick


def test_phase21q_second_run_uses_memory(tmp_path):
    memory_path = tmp_path / "hazard_memory.json"

    run_survival_pressure_hazard_adaptation_kernel(memory_path=memory_path, max_ticks=10)
    second = run_survival_pressure_hazard_adaptation_kernel(memory_path=memory_path, max_ticks=10)

    assert second.evidence["memory_loaded"] is True
    assert second.evidence["known_hazards"]
    assert second.evidence["uses_active_adaptation"] is True
    assert second.evidence["uses_persistent_memory"] is True
