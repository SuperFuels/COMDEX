# -*- coding: utf-8 -*-
"""
Photon ↔ SymPy Bridge Benchmark
===============================
Measures throughput and correctness of conversions:
  Photon → SymPy → Photon (lossless) and Photon → SymPy (boolean-lowered)
"""

import time
import statistics
import sympy as sp

from backend.photon_algebra.sympy_bridge import to_sympy, from_sympy
from backend.photon_algebra.tests.test_pp_roundtrip import photon_exprs
from backend.photon_algebra.rewriter import normalize


def benchmark_photon_sympy_bridge(n_samples: int = 4000):
    """Run roundtrip and measure average latency."""
    samples = [next(photon_exprs().example()) for _ in range(n_samples)]

    # warm-up
    for expr in samples[:50]:
        _ = from_sympy(to_sympy(expr, lossless=True))

    print("\n=== Photon↔SymPy Bridge Benchmark ===")
    print(f"Expressions:     {n_samples:,}")

    # Cold pass (no cache)
    t0 = time.perf_counter()
    for expr in samples:
        s = to_sympy(expr, lossless=True)
        back = from_sympy(s)
        assert normalize(back) == normalize(expr)
    t1 = time.perf_counter()
    cold_total = t1 - t0

    # Warm pass
    t2 = time.perf_counter()
    for expr in samples:
        _ = from_sympy(to_sympy(expr, lossless=True))
    t3 = time.perf_counter()
    warm_total = t3 - t2

    # Boolean-lowered test
    t4 = time.perf_counter()
    for expr in samples:
        _ = to_sympy(expr, lossless=False)
    t5 = time.perf_counter()
    lowered_total = t5 - t4

    print(f"Cold total:      {cold_total:.3f}s  ({n_samples / cold_total:,.1f} expr/s)")
    print(f"Warm total:      {warm_total:.3f}s  ({n_samples / warm_total:,.1f} expr/s)")
    print(f"Lowered total:   {lowered_total:.3f}s  ({n_samples / lowered_total:,.1f} expr/s)")
    print(f"Median op time:  {statistics.median([cold_total, warm_total, lowered_total]) * 1000 / n_samples:.3f} ms/op")
    print("======================================\n")


if __name__ == "__main__":
    benchmark_photon_sympy_bridge()