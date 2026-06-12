from backend.modules.aion_survival import run_multistep_lookahead_consequence_simulation_kernel


def test_phase21u_lookahead_changes_action_before_impact(tmp_path):
    result = run_multistep_lookahead_consequence_simulation_kernel(
        memory_path=tmp_path / "lookahead_memory.json",
        execution_depth=4,
    )

    assert result.kernel_version == "phase21u_multistep_lookahead_consequence_simulation_kernel_v1"
    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_multistep_lookahead"] is True
    assert result.evidence["uses_consequence_simulation"] is True
    assert result.lookahead_changed_action is True
    assert result.shallow_first_action == "right"
    assert result.deep_first_action == "down"
    assert result.avoided_future_hazard_before_impact is True
    assert result.hazards_hit == 0
    assert result.survived is True


def test_phase21u_deep_candidates_detect_future_hazard(tmp_path):
    result = run_multistep_lookahead_consequence_simulation_kernel(
        memory_path=tmp_path / "lookahead_memory.json",
        execution_depth=4,
    )

    right_candidate = next(c for c in result.deep_candidates if c["first_action"] == "right")
    selected_candidate = result.deep_candidates[0]

    assert right_candidate["predicted_hazard_count"] >= 1
    assert selected_candidate["first_action"] == "down"
    assert selected_candidate["predicted_hazard_count"] == 0


def test_phase21u_persists_lookahead_memory(tmp_path):
    memory_path = tmp_path / "lookahead_memory.json"

    first = run_multistep_lookahead_consequence_simulation_kernel(memory_path=memory_path)
    second = run_multistep_lookahead_consequence_simulation_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_policy["successful_lookahead_avoidances"] >= 2
    assert memory_path.exists()
