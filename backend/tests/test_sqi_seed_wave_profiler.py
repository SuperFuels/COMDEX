from pathlib import Path

from backend.modules.sqi.factor.seed_wave_profiler import profile_seed_wave


def test_seed_wave_profiler_finds_winners():
    n = 1000003 * 1009
    payload = profile_seed_wave(
        n,
        seed_count=16,
        max_steps_per_seed=10_000,
        rng_seed=123,
        method="brent",
    )
    assert payload["total_winners"] >= 1
    assert payload["best"]
    assert payload["best"][0]["verified"]
    assert Path(f"benchmarks/sqi_semiprime_lab/seed_wave_profile_{n}_brent.json").exists()
