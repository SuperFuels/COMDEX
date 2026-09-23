from datetime import datetime, timedelta, timezone

import json

from backend.modules.hexcore.week_scale_retention_challenge import continuous_observation_seconds, run


def test_long_downtime_resets_continuous_observation_span() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    hours = [0, 2, 4, 20, 22, 24]
    arena = {"cycles": [{"observed_at": (start + timedelta(hours=h)).isoformat()} for h in hours]}
    assert continuous_observation_seconds(arena) == 4 * 3600


def test_passed_retention_receipt_is_not_revoked_by_later_downtime(tmp_path) -> None:
    result_path = tmp_path / "results/retention.json"
    result_path.parent.mkdir(parents=True)
    result_path.write_text(json.dumps({
        "status": "PASSED", "passed": True, "contract": {"commitment": "sealed"},
        "tasks": {"protected_evidence_superset": True},
    }), encoding="utf-8")
    (tmp_path / "results/hexcore_long_duration_campaign_v15_state.json").write_text(
        json.dumps({"cycles": []}), encoding="utf-8"
    )
    preserved = run(repo_root=tmp_path, result_path=result_path)
    assert preserved["passed"] is True
    assert preserved["status"] == "PASSED"
    assert preserved["evidence_is_monotonic"] is True
