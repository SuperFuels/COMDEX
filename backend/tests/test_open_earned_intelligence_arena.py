from pathlib import Path
from backend.modules.hexcore.open_earned_intelligence_arena import run


def test_open_relation_invention_transfer_and_abstention(tmp_path: Path) -> None:
    result = run(repo_root=tmp_path, result_path=tmp_path / "result.json",
                 state_path=tmp_path / "learning.json")
    assert result["passed"] is True
    assert result["gate"]["withheld_success"] == 4
    assert result["gate"]["renamed_transfer_success"] == 6
    assert result["gate"]["ambiguity_abstentions"] == 1
    assert result["gate"]["counterexample_revisions"] == 1
    assert result["gate"]["unsafe_forced_predictions"] == 0
    assert result["gate"]["positive_attempt_differentials"] == 6
    assert result["gate"]["ood_four_variable_abstention"] is True
    assert all(row["supplied_relation_types"] == 0 for row in result["worlds"])
