from backend.modules.aion_survival import run_planning_under_uncertainty_kernel


def test_phase21x_unknown_entity_is_not_treated_as_safe_or_hostile(tmp_path):
    result = run_planning_under_uncertainty_kernel(memory_path=tmp_path / "uncertainty_memory.json")

    assert result.kernel_version == "phase21x_planning_under_uncertainty_kernel_v1"
    assert result.evidence["uses_llm_shortcut"] is False
    assert result.initial_risk_estimate == 0.5
    assert result.initial_confidence < 0.75
    assert result.direct_action_allowed is False
    assert result.initial_action == "observe_from_distance"
    assert result.avoided_overconfident_action is True


def test_phase21x_updates_risk_from_observations(tmp_path):
    result = run_planning_under_uncertainty_kernel(memory_path=tmp_path / "uncertainty_memory.json")

    assert result.evidence["uses_risk_update_from_observation"] is True
    assert result.evidence["observations_count"] == 3
    assert result.gathered_information_safely is True
    assert result.uncertainty_reduced is True
    assert result.final_risk_estimate >= 0.8
    assert result.final_confidence >= 0.75
    assert result.final_action == "take_wide_route"


def test_phase21x_persists_uncertainty_memory(tmp_path):
    memory_path = tmp_path / "uncertainty_memory.json"

    first = run_planning_under_uncertainty_kernel(memory_path=memory_path)
    second = run_planning_under_uncertainty_kernel(memory_path=memory_path)

    assert first.memory_loaded is False
    assert second.memory_loaded is True
    assert second.final_uncertainty_policy["safe_information_gathering_count"] >= 2
    assert second.final_uncertainty_policy["overconfident_actions_avoided"] >= 2
    assert memory_path.exists()
