from pathlib import Path

from backend.modules.sqi.factor.semiprime_confidence_sweep import run_confidence_sweep


def test_confidence_sweep_writes_report():
    payload = run_confidence_sweep(
        start_seed=123,
        runs=2,
        train_per_tier=1,
        eval_per_tier=1,
        spread_pairs=[(12, 20)],
        seed_count=16,
        max_steps=10_000,
    )

    assert payload["aggregate"]["runs"] == 2
    assert payload["aggregate"]["total_cases"] == 2
    assert "overall_solved_rate" in payload["aggregate"]
    assert Path(
        "benchmarks/sqi_semiprime_lab/generalization/confidence_sweep/semiprime_confidence_sweep_report.json"
    ).exists()
    assert Path(
        "benchmarks/sqi_semiprime_lab/generalization/confidence_sweep/semiprime_confidence_sweep_summary.json"
    ).exists()
