from backend.modules.aion_survival import run_curriculum_difficulty_escalation_kernel


def test_phase21t_runs_escalated_curriculum(tmp_path):
    memory_path = tmp_path / "escalation_memory.json"

    result = run_curriculum_difficulty_escalation_kernel(memory_path=memory_path)

    assert result.kernel_version == "phase21t_curriculum_difficulty_escalation_kernel_v1"
    assert result.escalation_worlds_run == 4
    assert result.escalation_worlds_survived == 4
    assert result.difficulty_improved is True
    assert result.difficulty_score_delta > 0
    assert result.final_score > result.baseline_score
    assert result.difficulty_score_delta > 0
    assert result.final_score > result.baseline_score
    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_curriculum_difficulty_escalation"] is True
    assert result.evidence["uses_harder_worlds"] is True
    assert result.evidence["uses_score_pressure"] is True
    assert memory_path.exists()


def test_phase21t_persists_escalation_memory(tmp_path):
    memory_path = tmp_path / "escalation_memory.json"

    first = run_curriculum_difficulty_escalation_kernel(memory_path=memory_path)
    second = run_curriculum_difficulty_escalation_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.evidence["memory_loaded"] is True
    assert second.escalation_worlds_survived == 4


def test_phase21t_records_world_result_fields(tmp_path):
    result = run_curriculum_difficulty_escalation_kernel(memory_path=tmp_path / "memory.json")
    world = result.world_results[-1]

    assert "world_id" in world
    assert "difficulty" in world
    assert "survived" in world
    assert "hazards_hit" in world
    assert "hazards_avoided" in world
    assert "reached_goal" in world
    assert "world_score" in world
    assert "route" in world
