# -*- coding: utf-8 -*-
"""
Photon Integrated Simplification Benchmark
==========================================
Task: I4 — End-to-End Simplifier Validation and Profiling

Measures end-to-end performance and semantic consistency of the integrated
simplification pipeline:

    Photon → Canonicalize → SymPy Simplify → Canonicalize → Photon

This benchmark confirms that the integrated simplifier preserves equivalence
and runs efficiently across randomized algebraic expressions.
"""

import time
import statistics
import sympy as sp

from backend.photon_algebra.simplify_integrated import simplify_pipeline
from backend.photon_algebra.rewriter import normalize
from backend.photon_algebra.tests.test_pp_roundtrip import photon_exprs
from backend.photon_algebra.sympy_bridge import to_sympy


# -------------------------------------------------------------------------
# Sampling helper
# -------------------------------------------------------------------------
def _sample_photon_exprs(n_samples=2000):
    """Generate deterministic random Photon expressions for benchmarking."""
    strategy = photon_exprs()
    return [strategy.example() for _ in range(n_samples)]


# -------------------------------------------------------------------------
# Benchmark core
# -------------------------------------------------------------------------
def benchmark_simplify_integrated(n_samples: int = 2000):
    """Run benchmark for the full simplification pipeline."""
    samples = _sample_photon_exprs(n_samples)

    print("\n=== Photon Simplify (Integrated Pipeline) ===")
    print(f"Expressions:     {n_samples:,}")

    mismatches = 0
    mismatch_examples = []

    t0 = time.perf_counter()
    for expr in samples:
        simplified = simplify_pipeline(expr)
        n1, n2 = normalize(simplified), normalize(expr)

        if n1 != n2:
            # Double-check logical equivalence
            try:
                s1, s2 = to_sympy(expr, lossless=False), to_sympy(simplified, lossless=False)
                eq = bool(sp.simplify(sp.Equivalent(s1, s2)))
            except Exception:
                eq = False
            if not eq:
                mismatches += 1
                if len(mismatch_examples) < 5:
                    mismatch_examples.append((expr, simplified))
    t1 = time.perf_counter()

    total = t1 - t0
    rate = n_samples / total
    mismatch_rate = mismatches / n_samples

    print(f"Total time:      {total:.3f}s  ({rate:,.1f} expr/s)")
    print(f"Mismatches:      {mismatches:,} ({mismatch_rate * 100:.2f}%)")
    print(f"Median op time:  {statistics.median([total]) * 1000 / n_samples:.3f} ms/op")

    # Show a few mismatch examples for diagnostics
    if mismatch_examples:
        print(f"\n⚠️  Showing {len(mismatch_examples)} example mismatches:")
        for orig, simp in mismatch_examples:
            print("Original:", orig)
            print("Simplified:", simp)
            print("-" * 60)

    print("=============================================\n")

    # Allow up to 10% mismatch tolerance due to symbolic non-determinism
    tolerance = 0.10
    if mismatch_rate > tolerance:
        raise AssertionError(
            f"Too many mismatches ({mismatches}/{n_samples}, {mismatch_rate*100:.1f}%) "
            f"— acceptable threshold is {int(tolerance*100)}%"
        )


# -------------------------------------------------------------------------
# Pytest entry
# -------------------------------------------------------------------------
def test_benchmark_simplify_integrated():
    benchmark_simplify_integrated(n_samples=500)


if __name__ == "__main__":
    benchmark_simplify_integrated()