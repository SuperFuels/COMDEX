from backend.modules.aion_survival import run_survival_planner_integration_kernel


def test_phase21z_integrates_all_survival_planning_layers(tmp_path):
    result = run_survival_planner_integration_kernel(
        memory_path=tmp_path / "integration_memory.json",
        runtime_root=tmp_path / "integration_runtime",
    )

    assert result.kernel_version == "phase21z_survival_planner_integration_kernel_v1"
    assert len(result.integrated_phases) == 6
    assert result.difficulty_escalation_passed is True
    assert result.lookahead_passed is True
    assert result.hazard_semantics_passed is True
    assert result.predator_passed is True
    assert result.uncertainty_passed is True
    assert result.self_plan_passed is True
    assert result.integration_passed is True
    assert result.evidence["uses_llm_shortcut"] is False


def test_phase21z_emits_planner_trace_and_receipt_hash(tmp_path):
    result = run_survival_planner_integration_kernel(
        memory_path=tmp_path / "integration_memory.json",
        runtime_root=tmp_path / "integration_runtime",
    )

    assert len(result.planner_receipt_hash) == 64
    assert "phase_results" in result.planner_trace
    assert "21T" in result.planner_trace["phase_results"]
    assert "21U" in result.planner_trace["phase_results"]
    assert "21V" in result.planner_trace["phase_results"]
    assert "21W" in result.planner_trace["phase_results"]
    assert "21X" in result.planner_trace["phase_results"]
    assert "21Y" in result.planner_trace["phase_results"]


def test_phase21z_persists_integration_memory(tmp_path):
    memory_path = tmp_path / "integration_memory.json"
    runtime_root = tmp_path / "integration_runtime"

    first = run_survival_planner_integration_kernel(memory_path=memory_path, runtime_root=runtime_root)
    second = run_survival_planner_integration_kernel(memory_path=memory_path, runtime_root=runtime_root)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_integration_policy["integration_run_count"] >= 2
    assert second.final_integration_policy["successful_integration_count"] >= 2
    assert memory_path.exists()
