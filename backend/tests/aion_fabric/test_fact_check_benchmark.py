from __future__ import annotations

from backend.modules.aion_fabric.fact_check_benchmark import LiveFactCheckBenchmark


def test_fact_check_benchmark_measures_fixed_verdicts_evidence_latency_and_errors(tmp_path):
    ticks = iter([0.0, 0.1, 1.0, 1.3])

    def checker(claim):
        if "false" in claim.lower():
            raise RuntimeError("provider unavailable")
        return {"verdict": "Supported", "provider": "aion_public_evidence", "sources": [{"url": "https://example.org/source"}]}

    report = LiveFactCheckBenchmark(tmp_path).run(
        [
            {"case_id": "supported", "claim": "This is a sufficiently long supported claim.", "expected_verdict": "Supported"},
            {"case_id": "false", "claim": "This is a sufficiently long false claim.", "expected_verdict": "False"},
        ],
        checker=checker,
        clock=lambda: next(ticks),
    )

    assert report["metrics"] == {"verdict_accuracy": 0.5, "https_evidence_coverage": 0.5, "mean_latency_ms": 200.0, "p95_latency_ms": 300, "error_count": 1}
    assert report["interpretation"]["benchmark_is_not_model_self_grading"] is True
    assert LiveFactCheckBenchmark(tmp_path).latest()["report_hash"] == report["report_hash"]
