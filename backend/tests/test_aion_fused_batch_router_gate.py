from backend.scripts.run_aion_fused_batch_router_gate import _summary


def test_summary_reports_nearest_rank_tail() -> None:
    result = _summary([0.004, 0.001, 0.003, 0.002])
    assert result["p50_seconds"] == 0.0025
    assert result["p95_seconds_nearest_rank"] == 0.004
