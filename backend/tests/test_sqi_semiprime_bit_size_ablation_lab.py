from __future__ import annotations

from backend.modules.sqi.factor.semiprime_bit_size_ablation_lab import (
    parse_spread_pairs,
    run_bit_size_ablation,
)


def test_parse_spread_pairs():
    assert parse_spread_pairs("40x64,48x72") == ["40x64", "48x72"]


def test_bit_size_ablation_smoke(tmp_path):
    out = run_bit_size_ablation(
        spread_pairs=["20x28"],
        train_per_tier=1,
        eval_per_tier=1,
        seed_count=16,
        max_steps=10000,
        base_seed=20260508,
        out_dir=tmp_path,
    )

    assert out["aggregate"]["tiers"] == 1
    assert out["tiers"][0]["spread_pair"] == "20x28"
    assert out["tiers"][0]["total_eval_cases"] == 1
    assert 0 <= out["tiers"][0]["sqi_solved_rate"] <= 1
    assert (tmp_path / "semiprime_bit_size_ablation_report.json").exists()
    assert (tmp_path / "semiprime_bit_size_ablation_summary.json").exists()
