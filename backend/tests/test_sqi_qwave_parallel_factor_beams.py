from backend.modules.sqi.factor.qwave_parallel_factor_beams import (
    benchmark_parallel_qwave,
    parallel_qwave_seed_beam_search,
)


def test_parallel_qwave_seed_beam_search_finds_small_spread_factor():
    n = 1000003 * 1009

    factor, checks, trace, method = parallel_qwave_seed_beam_search(
        n,
        beam_count=2,
        seeds_per_beam=16,
        max_steps_per_seed=20_000,
        prefer="brent",
        rng_seed=12345,
    )

    assert factor in {1000003, 1009}
    assert n % factor == 0
    assert checks > 0
    assert trace
    assert method.startswith("parallel_qwave_")


def test_parallel_qwave_benchmark_payload():
    n = 10007 * 10009

    out = benchmark_parallel_qwave(
        n,
        beam_count=2,
        seeds_per_beam=8,
        max_steps_per_seed=10_000,
        prefer="brent",
    )

    assert out["verified"] is True
    assert out["factor"] in {10007, 10009}
    assert out["factor"] * out["cofactor"] == n
    assert out["beam_count"] == 2
