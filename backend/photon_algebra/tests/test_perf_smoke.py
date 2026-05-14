# backend/photon_algebra/tests/test_perf_smoke.py
import time
import random
import pytest
from backend.photon_algebra.rewriter import (
    clear_normalize_memo,
    get_cache_stats,
    rewriter,  # 👈 directly import the wrapper instance
)


def random_expr(depth=3, symbols=("a", "b", "c", "d")) -> str:
    """Generate a random photon glyph expression (string form)."""
    if depth == 0 or random.random() < 0.3:
        return random.choice(symbols)

    op = random.choice(["⊕", "⊗", "⊖"])
    left = random_expr(depth - 1, symbols)
    right = random_expr(depth - 1, symbols)
    return {"op": op, "states": [left, right]}  # return structured dict, not string


@pytest.mark.slow
def test_perf_caching_vs_cold():
    """Sanity check that caching gives us a speedup and correctness holds."""

    exprs = [random_expr(depth=4) for _ in range(500)]

    # --- Cold run (memo cleared) ---
    clear_normalize_memo()
    t0 = time.time()
    cold_results = [rewriter.normalize(e) for e in exprs]
    cold_time = time.time() - t0
    cold_stats = get_cache_stats()

    # --- Warm run (same exprs; cache hits) ---
    t1 = time.time()
    warm_results = [rewriter.normalize(e) for e in exprs]
    warm_time = time.time() - t1
    warm_stats = get_cache_stats()

    # Correctness
    assert cold_results == warm_results

    # Idempotence: normalize(normalize(e)) == normalize(e)
    for e in exprs[:50]:
        n1 = rewriter.normalize(e)
        n2 = rewriter.normalize(n1)
        assert n1 == n2  # dict/str equality

    print(
        f"\nPerf cold: {cold_time:.3f}s, warm: {warm_time:.3f}s "
        f"(speedup ≈ {cold_time/warm_time:.2f}x)"
    )
    print("Cache stats after warm run:", warm_stats)

    assert warm_time < cold_time


def test_cache_stats_reporting():
    clear_normalize_memo()
    _ = rewriter.normalize({"op": "⊕", "states": ["a", "b"]})
    _ = rewriter.normalize({"op": "⊕", "states": ["a", "b"]})  # cache hit
    stats = get_cache_stats()
    assert stats["misses"] == 1
    assert stats["hits"] == 1