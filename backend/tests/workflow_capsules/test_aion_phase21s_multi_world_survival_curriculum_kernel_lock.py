from backend.modules.aion_survival import run_multi_world_survival_curriculum_kernel


def test_phase21s_runs_multiple_survival_worlds(tmp_path):
    memory_path = tmp_path / "curriculum_memory.json"

    result = run_multi_world_survival_curriculum_kernel(
        memory_path=memory_path,
        max_ticks_per_world=10,
    )

    assert result.kernel_version == "phase21s_multi_world_survival_curriculum_kernel_v1"
    assert result.worlds_run == 3
    assert result.worlds_survived == 3
    assert result.curriculum_score > 0
    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_multi_world_curriculum"] is True
    assert result.evidence["uses_food_seeking_transfer"] is True
    assert result.evidence["uses_hazard_avoidance_transfer"] is True
    assert result.evidence["uses_goal_seeking_transfer"] is True
    assert memory_path.exists()


def test_phase21s_persists_curriculum_memory(tmp_path):
    memory_path = tmp_path / "curriculum_memory.json"

    first = run_multi_world_survival_curriculum_kernel(memory_path=memory_path)
    second = run_multi_world_survival_curriculum_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.evidence["memory_loaded"] is True
    assert second.worlds_survived == 3


def test_phase21s_records_world_results(tmp_path):
    memory_path = tmp_path / "curriculum_memory.json"

    result = run_multi_world_survival_curriculum_kernel(memory_path=memory_path)
    first_world = result.world_results[0]

    assert "world_id" in first_world
    assert "survived" in first_world
    assert "food_collected" in first_world
    assert "hazards_hit" in first_world
    assert "hazards_avoided" in first_world
    assert "route" in first_world
    assert "learned_concepts" in first_world
