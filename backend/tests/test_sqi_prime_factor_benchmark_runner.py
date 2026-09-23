from pathlib import Path

from backend.modules.sqi.factor.sqi_prime_factorizer import (
    benchmark,
    run_large_benchmark_table,
    sqi_factor_once,
)


def test_close_semiprime_uses_fermat():
    n = 10007 * 10009
    out = benchmark(n)
    assert out["sqi"]["factor"] in {10007, 10009}
    assert out["sqi"]["method"] == "fermat"


def test_spread_semiprime_finds_factor():
    n = 1000003 * 1009
    out = benchmark(n)
    assert out["sqi"]["factor"] in {1000003, 1009}
    assert out["sqi"]["factor"] * out["sqi"]["cofactor"] == n


def test_less_close_semiprime_finds_factor():
    n = 10007 * 20011
    out = benchmark(n)
    assert out["sqi"]["factor"] in {10007, 20011}
    assert out["sqi"]["factor"] * out["sqi"]["cofactor"] == n


def test_adaptive_routing_prefers_rho_for_spread_case():
    n = 1000003 * 1009
    result = sqi_factor_once(n)
    routing = [x for x in result.trace if x.get("event") == "branch_routing"][0]
    assert routing["order"][0] in {"brent_rho", "pollard_rho"}
    assert result.found_factor in {1000003, 1009}


def test_trace_and_dashboard_artifacts_are_written():
    n = 10007 * 10009
    result = sqi_factor_once(n)
    assert result.trace_path
    assert result.dashboard_path
    assert Path(result.trace_path).exists()
    assert Path(result.dashboard_path).exists()


def test_large_benchmark_table_writes_outputs():
    rows = run_large_benchmark_table()
    assert rows
    assert Path("benchmarks/sqi_prime_factor_benchmark_v2.json").exists()
    assert Path("benchmarks/sqi_prime_factor_dashboard_v2.json").exists()
