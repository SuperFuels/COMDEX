from backend.modules.aion_survival import run_self_generated_survival_plan_kernel


def test_phase21y_generates_labelled_survival_plan(tmp_path):
    result = run_self_generated_survival_plan_kernel(memory_path=tmp_path / "plan_memory.json")

    assert result.kernel_version == "phase21y_self_generated_survival_plan_kernel_v1"
    assert result.plan_generated is True
    assert result.plan_goal == "reach_goal_without_hazard_impact"
    assert len(result.plan_steps) >= 6
    assert result.fallback_route_present is True
    assert result.uncertainty_label_present is True
    assert result.hazard_label_present is True
    assert "goal" in result.plan_labels
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase21y_revises_plan_when_world_changes(tmp_path):
    result = run_self_generated_survival_plan_kernel(memory_path=tmp_path / "plan_memory.json")

    assert result.plan_revision_count >= 1
    assert result.plan_updated_when_world_changed is True
    assert result.survived is True
    assert result.goal_reached is True
    assert any(step["event"] == "world_changed_predator_blocks_upper_route" for step in result.execution_trace)
    assert any(rev["trigger"] == "predator_blocks_upper_route" for rev in result.plan_revisions)


def test_phase21y_persists_plan_memory(tmp_path):
    memory_path = tmp_path / "plan_memory.json"

    first = run_self_generated_survival_plan_kernel(memory_path=memory_path)
    second = run_self_generated_survival_plan_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_plan_policy["plan_generation_count"] >= 2
    assert second.final_plan_policy["plan_revision_count"] >= 2
    assert second.final_plan_policy["successful_plan_execution_count"] >= 2
    assert memory_path.exists()
