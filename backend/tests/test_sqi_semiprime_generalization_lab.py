from pathlib import Path

from backend.modules.sqi.factor.semiprime_generalization_lab import (
    run_generalization_lab,
    train_seed_priors,
)
from backend.modules.sqi.factor.semiprime_lab import build_cases


def test_train_seed_priors_shape():
    cases = build_cases(
        seed=123,
        close_bits=[],
        spread_pairs=[(12, 20)],
        per_tier=1,
    )
    out = train_seed_priors(cases, seed_count=16, max_steps=10_000)
    assert "priors" in out
    assert "learned_seed_pairs" in out


def test_generalization_lab_writes_report():
    payload = run_generalization_lab(
        seed=123,
        train_per_tier=1,
        eval_per_tier=1,
        spread_pairs=[(12, 20)],
        seed_count=16,
        max_steps=10_000,
    )
    assert payload["summary"]["total_eval_cases"] == 1
    assert Path("benchmarks/sqi_semiprime_lab/generalization/semiprime_generalization_report.json").exists()
    assert Path("benchmarks/sqi_semiprime_lab/generalization/semiprime_generalization_summary.json").exists()


def test_generalization_lab_uses_ladder_method():
    payload = run_generalization_lab(
        seed=456,
        train_per_tier=1,
        eval_per_tier=1,
        spread_pairs=[(12, 20)],
        seed_count=16,
        max_steps=10_000,
    )
    method = payload["evaluation"][0]["sqi"]["method"]
    assert "seed_wave_ladder" in method or method == "adaptive_seed_wave_ladder_none"
