from backend.modules.sqi.factor.sqi_prime_factorizer import (
    benchmark,
    brent_rho_factor,
    factor_recursive,
    miller_rabin_is_probable_prime,
    sqi_factor_once,
)


def test_miller_rabin_prime_gate():
    assert miller_rabin_is_probable_prime(101)
    assert miller_rabin_is_probable_prime(1000003)
    assert not miller_rabin_is_probable_prime(91)
    assert not miller_rabin_is_probable_prime(10007 * 10009)


def test_sqi_factor_easy_composite():
    result = sqi_factor_once(91)
    assert result.found_factor in {7, 13}
    assert result.found_factor * result.cofactor == 91


def test_sqi_factor_8051():
    result = sqi_factor_once(8051)
    assert result.found_factor in {83, 97}
    assert result.found_factor * result.cofactor == 8051


def test_sqi_factor_close_semiprime():
    n = 10007 * 10009
    result = sqi_factor_once(n)
    assert result.found_factor in {10007, 10009}
    assert result.found_factor * result.cofactor == n


def test_brent_rho_finds_factor():
    n = 1000003 * 1009
    factor, checks, trace = brent_rho_factor(n, seed=8739, c=23, max_steps=25_000)
    assert factor in {1000003, 1009}
    assert n % factor == 0
    assert checks > 0
    assert trace


def test_sqi_recursive_factorization():
    factors = factor_recursive(2 * 3 * 5 * 97)
    assert sorted(factors) == [2, 3, 5, 97]


def test_sqi_benchmark_shape():
    out = benchmark(10403)
    assert out["n"] == 10403
    assert "naive" in out
    assert "wheel" in out
    assert "fermat_only" in out
    assert "pollard_only" in out
    assert "brent_only" in out
    assert "sqi" in out
    assert "full_factorization" in out
    assert out["sqi"]["factor"] is not None


def test_sqi_factor_accepts_deep_rho_budget_parameters():
    n = 1000003 * 1009
    result = sqi_factor_once(
        n,
        rho_branches=4,
        rho_step_budget=50_000,
        rho_active_branches=2,
        trace_jsonl=False,
        dashboard_json=False,
    )
    assert result.found_factor in {1000003, 1009}
    assert result.found_factor * result.cofactor == n


def test_rho_seed_wave_search_finds_known_spread_factor():
    from backend.modules.sqi.factor.sqi_prime_factorizer import rho_seed_wave_search

    n = 1000003 * 1009
    factor, checks, trace = rho_seed_wave_search(
        n,
        seed_count=16,
        max_steps_per_seed=10_000,
        rng_seed=123,
    )
    assert factor in {1000003, 1009}
    assert n % factor == 0
    assert checks > 0
    assert trace


def test_rho_seed_wave_accepts_learned_priors():
    from backend.modules.sqi.factor.sqi_prime_factorizer import rho_seed_wave_search

    n = 1000003 * 1009
    factor, checks, trace = rho_seed_wave_search(
        n,
        seed_count=16,
        max_steps_per_seed=10_000,
        learned_seed_priors=[(15, 14)],
    )
    assert factor in {1000003, 1009}
    assert n % factor == 0
    assert checks > 0
    assert trace


def test_adaptive_seed_wave_ladder_finds_known_spread_factor():
    from backend.modules.sqi.factor.sqi_prime_factorizer import adaptive_seed_wave_ladder

    n = 1000003 * 1009
    factor, checks, trace, method = adaptive_seed_wave_ladder(
        n,
        learned_seed_priors=[(15, 14)],
        rng_seed=123,
    )
    assert factor in {1000003, 1009}
    assert n % factor == 0
    assert checks > 0
    assert trace
    assert method != "adaptive_seed_wave_ladder_none"
