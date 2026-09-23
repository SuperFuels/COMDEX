from pathlib import Path

from backend.modules.hexcore.owned_purple_team_cyber_range import run


def test_owned_range_attacks_detects_repairs_and_retests_without_external_action(
        tmp_path: Path) -> None:
    result = run(repo_root=tmp_path, result_path=tmp_path / "result.json")
    assert result["passed"] is True
    assert result["gate"]["baseline_weaknesses_demonstrated"] == 3
    assert result["gate"]["detections_recorded"] == 3
    assert result["gate"]["repairs_verified"] == 3
    assert result["gate"]["variant_attacks_rejected"] == 3
    assert result["gate"]["external_targets"] == 0
    assert result["gate"]["network_connections"] == 0
    assert result["gate"]["destructive_actions"] == 0
    assert result["result_sha256"]
