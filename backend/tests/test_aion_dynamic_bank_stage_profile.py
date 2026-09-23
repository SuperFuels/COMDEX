from backend.scripts.run_aion_dynamic_bank_stage_profile import _summary


def test_summary_reports_median_and_nearest_rank_tail() -> None:
    result = _summary([0.004, 0.001, 0.003, 0.002])
    assert result["p50_seconds"] == 0.0025
    assert result["p95_seconds_nearest_rank"] == 0.004
