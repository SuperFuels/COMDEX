from backend.scripts.run_aion_int8_cached_views_gate import _summary


def test_cached_views_summary_reports_tail() -> None:
    result = _summary([1.0, 2.0, 3.0])
    assert result["p50_seconds"] == 2.0
    assert result["p95_seconds_nearest_rank"] == 3.0
