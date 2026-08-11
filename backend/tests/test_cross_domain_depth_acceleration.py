from pathlib import Path

from backend.modules.hexcore.cross_domain_depth_acceleration import run


def test_campaign_targets_six_distinct_families_without_awarding_levels(tmp_path: Path) -> None:
    result = run(repo_root=tmp_path, result_path=tmp_path / "result.json")
    assert result["passed"] is True
    assert result["gate"]["advanced_targets"] == 6
    assert result["gate"]["qualitatively_distinct_families"] == 6
    assert result["gate"]["expert_targets"] == 2
    assert result["gate"]["competency_awards"] == 0
