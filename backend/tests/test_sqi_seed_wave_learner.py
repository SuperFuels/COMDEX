from pathlib import Path

from backend.modules.sqi.factor.seed_wave_learner import (
    build_priors,
    feature_rows,
    near_square_features,
    write_priors,
)
from backend.modules.sqi.factor.semiprime_lab import run_lab


def test_near_square_features():
    n = 10007 * 10009
    gap, score = near_square_features(n)
    assert gap == 1
    assert score > 0.99


def test_feature_rows_and_priors_from_lab():
    report = run_lab(
        seed=123,
        close_bits=[16],
        spread_pairs=[(12, 20)],
        per_tier=1,
        trace=False,
        dashboard=False,
    )
    rows = feature_rows(report)
    assert len(rows) == 2

    priors = build_priors(rows)
    assert priors["total_rows"] == 2
    assert priors["buckets"]


def test_write_priors_file():
    run_lab(
        seed=123,
        close_bits=[16],
        spread_pairs=[(12, 20)],
        per_tier=1,
        trace=False,
        dashboard=False,
    )
    priors = write_priors()
    assert priors["total_rows"] == 2
    assert Path("benchmarks/sqi_semiprime_lab/seed_wave_priors.json").exists()
