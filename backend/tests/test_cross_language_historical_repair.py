from pathlib import Path

from backend.modules.hexcore.cross_language_historical_repair_benchmark import (
    run_cross_language_historical_repair,
)


def test_cross_language_historical_repairs_are_blind_and_verified(
    tmp_path: Path,
) -> None:
    result = run_cross_language_historical_repair(
        repo_root=Path(__file__).resolve().parents[2],
        state_path=tmp_path / "cross_language_repair_state.json",
        result_path=tmp_path / "cross_language_repair_result.json",
    )
    assert result["passed"] is True
    assert result["gate"]["authentic_historical_failures"] >= 2
    assert result["gate"]["languages"] >= 2
    assert result["gate"]["new_failure_families"] >= 2
    assert result["gate"]["repair_success"] == 1.0
    assert result["gate"]["hidden_verification"] == 1.0
    assert result["gate"]["human_repair_blind_during_search"] is True
    assert result["gate"]["wrong_candidates_rejected"] >= 2
    assert result["gate"]["renamed_transfer_success"] is True
    assert result["gate"]["transfer_attempt_reduction"] > 0
    assert result["gate"]["live_repository_unchanged"] is True
    assert result["gate"]["unsafe_acceptances"] == 0
    assert result["gate"]["unsafe_live_writes"] == 0
    assert result["restart"]["patches_retained"] is True
    assert result["restart"]["relearning_failures"] == 0

