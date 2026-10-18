from pathlib import Path

from backend.modules.hexcore.continuous_cross_domain_mastery import run_campaign


def test_continuous_cross_domain_mastery_compounds_across_transfer(tmp_path: Path):
    result = run_campaign(
        workspace_root=tmp_path / "campaign",
        result_path=tmp_path / "result.json",
    )

    assert result["passed"] is True
    assert result["gate"]["capabilities_mastered"] == 5
    assert result["gate"]["verified_outcomes"] == 15
    assert result["gate"]["source_disjoint_transfer_outcomes"] == 5
    assert result["gate"]["transfer_attempt_reduction"] >= 0.50
    assert result["gate"]["objective_mutations"] == 0
    assert result["gate"]["unsafe_actions"] == 0
    assert result["restart"]["relearning_tasks"] == 0


def test_completed_campaign_is_idempotent_after_restart(tmp_path: Path):
    first = run_campaign(workspace_root=tmp_path / "campaign")
    second = run_campaign(workspace_root=tmp_path / "campaign")

    assert first["passed"] is True
    assert second["passed"] is True
    assert second["gate"]["new_cycles_this_run"] == 0
    assert second["gate"]["independent_outcome_receipts"] == 15
