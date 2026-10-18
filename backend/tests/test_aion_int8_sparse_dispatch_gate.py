import torch

from backend.scripts.run_aion_int8_sparse_dispatch_gate import _summary


def test_sparse_dispatch_summary_reports_median_and_p95() -> None:
    result = _summary([0.1, 0.2, 0.3, 0.4, 0.5])
    assert result["p50_seconds"] == 0.3
    assert result["p95_seconds_nearest_rank"] == 0.5
    assert abs(result["mean_seconds"] - 0.3) < 1e-12
