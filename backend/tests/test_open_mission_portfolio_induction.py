from pathlib import Path

import pytest

from backend.modules.hexcore.open_mission_portfolio_induction import (
    OpenMissionInducer,
    RawPortfolio,
    run,
)


def test_inducer_builds_variable_dependency_graph_from_raw_interfaces(tmp_path: Path):
    (tmp_path / "evidence.md").write_text("A sourced explanation.", encoding="utf-8")
    (tmp_path / "measurements.csv").write_text("x,y\n1,2\n", encoding="utf-8")
    mission = OpenMissionInducer().induce(RawPortfolio(
        "novel",
        "transfer",
        "Compare the numerical evidence with the written claim.",
        (tmp_path / "evidence.md", tmp_path / "measurements.csv"),
    ))

    names = {row["capability"] for row in mission["induction"]["capability_graph"]}
    assert "natural_document_comprehension" in names
    assert "quantitative_table_reasoning" in names
    assert "cross_modal_synthesis" in names
    assert "quantitative_claim_verification" in names
    assert all(row["minimum_transfer_outcomes"] == 1 for row in mission["capability_requirements"])


def test_inducer_rejects_empty_portfolio():
    with pytest.raises(ValueError):
        OpenMissionInducer().induce(RawPortfolio("empty", "development", "Do something", ()))


def test_open_mission_campaign_compiles_and_retains_real_portfolios(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[2]
    result = run(repo_root=repo_root, workspace_root=tmp_path / "campaign", result_path=tmp_path / "result.json")

    assert result["passed"] is True
    assert result["gate"]["missions_completed"] == 4
    assert result["gate"]["invented_capability_nodes"] == 24
    assert result["gate"]["verified_runtime_cycles"] == 24
    assert result["gate"]["weakest_portfolio_success"] == 1.0
    assert result["gate"]["open_induction_coverage"] > result["gate"]["fixed_curriculum_mean_coverage"]
    assert result["gate"]["transfer_information_action_reduction"] > 0.0
    assert result["gate"]["terminal_objective_mutations"] == 0
    assert result["restart"]["relearning_tasks"] == 0
