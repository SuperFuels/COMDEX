from pathlib import Path

from backend.modules.hexcore.mission_capability_action_harness import MissionCapabilityActionHarness
from backend.modules.hexcore.progressive_competency_system import ProgressiveCompetencySystem


def test_top_level_domains_expand_to_leaf_subjects_and_subskills(tmp_path: Path):
    system = ProgressiveCompetencySystem(repo_root=tmp_path, state_path=tmp_path / "state.json")
    domains = system.domain_assessments()
    assert len(domains) == 15
    systems = domains["systems_software"]
    assert systems["subject_count"] >= 6
    assert systems["subskills_declared"] >= 40
    assert systems["target_reached"] is False


def test_natural_mission_checks_knowledge_before_action_and_selects_stack(tmp_path: Path):
    harness = MissionCapabilityActionHarness(repo_root=tmp_path, state_path=tmp_path / "state.json")
    result = harness.evaluate({
        "goal_id": "weather-app",
        "goal": "Build a secure browser weather app with an API and persistent user settings",
    }, register_learning=True)
    subject_ids = {row["subject_id"] for row in result["requirements"]}
    assert result["decision"] == "learn_then_execute"
    assert "software_engineering" in subject_ids
    assert result["technology_proposal"]["stack"] == ["TypeScript", "HTML/CSS"]
    assert harness.system.state["mission_demands"]
    assert len(result["action_contract"]) == 8


def test_unknown_objective_does_not_force_unrelated_action(tmp_path: Path):
    harness = MissionCapabilityActionHarness(repo_root=tmp_path, state_path=tmp_path / "state.json")
    result = harness.evaluate({"goal": "Florp the zibble without any described outcome"})
    assert result["decision"] == "clarify"
    assert result["reason"] == "no_grounded_capability_mapping"


def test_router_separates_single_domain_from_cross_domain_work(tmp_path: Path):
    # Seed the same subject catalogue; routing itself must remain independent
    # of the achieved levels in this isolated test.
    harness = MissionCapabilityActionHarness(repo_root=tmp_path, state_path=tmp_path / "state.json")
    single = harness.infer_subjects(
        "Design a deterministic graph algorithm that orders dependency nodes and rejects cycles"
    )
    mixed = harness.infer_subjects(
        "Diagnose and repair a dependency-graph scheduler, then invent executable regression "
        "and counterexample tests that reject cycles and missing dependencies"
    )
    assert single == ["algorithms_data_structures"]
    assert mixed == ["algorithms_data_structures", "testing_debugging"]
