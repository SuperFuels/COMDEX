"""
Photon Algebra — Benchmark normalize() performance and caching efficiency
(Task: I1.4 — Runtime Performance Loop Benchmark + Cache Warm Run)
"""

import time
import random
import statistics
from backend.photon_algebra.rewriter import normalize, get_cache_stats, DIAG, _NORMALIZE_MEMO
from backend.photon_algebra.core import EMPTY, TOP, BOTTOM

OPS = ["⊕", "⊗", "⊖", "↔", "¬", "★"]
ATOMS = ["a", "b", "c", "d", "e", "x", "y", "z"]

# -----------------------------------------------------------------------------
# Expression generator
# -----------------------------------------------------------------------------

def random_expr(depth=4):
    """Recursively generate a random Photon expression tree."""
    if depth <= 0:
        return random.choice(ATOMS)
    op = random.choice(OPS)
    if op in {"¬", "★"}:
        return {"op": op, "state": random_expr(depth - 1)}
    elif op in {"⊕", "⊗", "⊖", "↔"}:
        n = random.randint(2, 4)
        return {"op": op, "states": [random_expr(depth - 1) for _ in range(n)]}
    else:
        return random.choice([EMPTY, TOP, BOTTOM, random.choice(ATOMS)])

# -----------------------------------------------------------------------------
# Benchmark routines
# -----------------------------------------------------------------------------

def benchmark_normalize(N=5000, depth=5, warmup=200):
    """Run normalize() N times and report timing and cache diagnostics."""
    exprs = [random_expr(depth) for _ in range(N)]

    # Cold pass
    _NORMALIZE_MEMO.clear()
    t0 = time.time()
    times = []
    for e in exprs:
        t1 = time.time()
        normalize(e)
        times.append(time.time() - t1)
    cold_elapsed = time.time() - t0

    # Warm pass (cache hot)
    _NORMALIZE_MEMO.clear()
    warm_samples = exprs[:min(warmup, N)]
    for e in warm_samples:
        normalize(e)  # populate cache

    t2 = time.time()
    for e in exprs:
        normalize(random.choice(warm_samples))
    warm_elapsed = time.time() - t2

    stats = get_cache_stats()
    diag = getattr(
        DIAG,
        "to_dict",
        lambda: {k: getattr(DIAG, k) for k in dir(DIAG) if not k.startswith("_")}
    )()

    print("\n=== Photon Normalize Benchmark ===")
    print(f"Expressions:     {N:,}")
    print(f"Avg depth:       {depth}")
    print(f"Cold total:      {cold_elapsed:.3f}s  ({N / cold_elapsed:.1f} expr/s)")
    print(f"Warm total:      {warm_elapsed:.3f}s  ({N / warm_elapsed:.1f} expr/s)")
    print(f"Median op time:  {statistics.median(times) * 1000:.3f} ms")
    print("Cache stats:", stats)
    print("Diagnostics:", diag)
    print("==================================\n")

    # Sanity check
    assert cold_elapsed < 30, "Cold normalization took too long — check recursion"
    assert warm_elapsed < cold_elapsed, "Warm (cached) run slower than cold — cache issue?"

# -----------------------------------------------------------------------------
# Pytest-compatible test
# -----------------------------------------------------------------------------

def test_benchmark_normalize():
    """pytest entrypoint for automated benchmark run"""
    # Next level: 6,000 expressions, slightly deeper nesting (depth 6)
    benchmark_normalize(N=6000, depth=6)


# -----------------------------------------------------------------------------
# CLI entry
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    print("Running Photon Algebra normalize() benchmark...")
    # Heavier CLI stress test: 3,000 expressions at depth 7
    benchmark_normalize(N=3000, depth=7)