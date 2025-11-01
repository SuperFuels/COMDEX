# -*- coding: utf-8 -*-
"""
Photon Serialization & Interop Benchmark
========================================
Task: I5 - Validate JSON↔Photon↔SymPy roundtrip fidelity.
"""

import time
import statistics
from backend.photon_algebra.serialize_interop import validate_roundtrip
from backend.photon_algebra.tests.test_pp_roundtrip import photon_exprs

# -------------------------------------------------------------------------
def _sample_photon_exprs(n_samples=2000):
    strategy = photon_exprs()
    return [strategy.example() for _ in range(n_samples)]

# -------------------------------------------------------------------------
def benchmark_serialize_interop(n_samples=2000):
    samples = _sample_photon_exprs(n_samples)

    print("\n=== Photon JSON↔SymPy Interop Benchmark ===")
    print(f"Expressions:     {n_samples:,}")

    mismatches = 0
    t0 = time.perf_counter()
    for expr in samples:
        if not validate_roundtrip(expr, simplify=True):
            mismatches += 1
    t1 = time.perf_counter()

    total = t1 - t0
    rate = n_samples / total

    print(f"Total time:      {total:.3f}s  ({rate:,.1f} expr/s)")
    print(f"Mismatches:      {mismatches:,} ({(mismatches / n_samples) * 100:.2f}%)")
    print(f"Median op time:  {statistics.median([total]) * 1000 / n_samples:.3f} ms/op")
    print("===========================================")

    assert mismatches < n_samples * 0.02, f"Too many mismatches ({mismatches}/{n_samples})"

# -------------------------------------------------------------------------
def test_benchmark_serialize_interop():
    benchmark_serialize_interop(n_samples=500)

if __name__ == "__main__":
    benchmark_serialize_interop()


if __name__ == "__main__":
    # Manual invocation bypassing pytest
    from backend.photon_algebra.tests.bench_serialize_interop import benchmark_serialize_interop
    benchmark_serialize_interop(n_samples=500)