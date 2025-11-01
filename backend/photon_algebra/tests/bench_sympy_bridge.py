# -*- coding: utf-8 -*-
"""
Photon ↔ SymPy Bridge Benchmark
===============================
Measures throughput and correctness of conversions:
  Photon -> SymPy -> Photon (lossless)
  Photon -> SymPy (boolean-lowered)
"""

import time
import statistics
import sympy as sp

from backend.photon_algebra.sympy_bridge import to_sympy, from_sympy
from backend.photon_algebra.tests.test_pp_roundtrip import photon_exprs
from backend.photon_algebra.rewriter import normalize


COMMUTATIVE_OPS = {"⊕", "⊗", "≈", "↔", "⊖", "⊂"}


def _canonicalize(expr):
    """Sort symmetric operands for commutative ops to make equality stable."""
    if not isinstance(expr, dict):
        return expr
    op = expr.get("op")
    if op in COMMUTATIVE_OPS and "states" in expr:
        states = sorted((_canonicalize(s) for s in expr["states"]), key=lambda x: str(x))
        return {"op": op, "states": states}
    if "state" in expr:
        return {"op": op, "state": _canonicalize(expr["state"])}
    if "states" in expr:
        return {"op": op, "states": [_canonicalize(s) for s in expr["states"]]}
    return expr


def _equalish(a, b):
    """Looser equality allowing tautological equivalences (↔(x,x)->⊤, ⊂(⊥,x)->⊤)."""
    if a == b:
        return True

    # ↔(x,x) ≡ ⊤
    if (
        isinstance(a, dict)
        and a.get("op") == "↔"
        and len(a.get("states", [])) == 2
        and a["states"][0] == a["states"][1]
        and b == {"op": "⊤"}
    ):
        return True
    if (
        isinstance(b, dict)
        and b.get("op") == "↔"
        and len(b.get("states", [])) == 2
        and b["states"][0] == b["states"][1]
        and a == {"op": "⊤"}
    ):
        return True

    # ⊂(⊥, x) ≡ ⊤ (bottom is subset of everything)
    if (
        isinstance(a, dict)
        and a.get("op") == "⊂"
        and len(a.get("states", [])) == 2
        and a["states"][0] == {"op": "⊥"}
        and b == {"op": "⊤"}
    ):
        return True
    if (
        isinstance(b, dict)
        and b.get("op") == "⊂"
        and len(b.get("states", [])) == 2
        and b["states"][0] == {"op": "⊥"}
        and a == {"op": "⊤"}
    ):
        return True

    return False


def _sample_photon_exprs(n_samples=4000):
    strategy = photon_exprs()
    return [strategy.example() for _ in range(n_samples)]


def benchmark_photon_sympy_bridge(n_samples: int = 4000):
    samples = _sample_photon_exprs(n_samples)

    # warm-up
    for expr in samples[:50]:
        _ = from_sympy(to_sympy(expr, lossless=True))

    print("\n=== Photon↔SymPy Bridge Benchmark ===")
    print(f"Expressions:     {n_samples:,}")

    mismatches = []

    # Cold roundtrip
    t0 = time.perf_counter()
    for i, expr in enumerate(samples):
        s = to_sympy(expr, lossless=True)
        back = from_sympy(s)
        n_expr = _canonicalize(normalize(expr))
        n_back = _canonicalize(normalize(back))
        if not _equalish(n_expr, n_back):
            mismatches.append((i, n_expr, n_back, s))
    t1 = time.perf_counter()
    cold_total = t1 - t0

    if mismatches:
        i, orig, back, sym = mismatches[0]
        print(f"\n❌ Mismatch at sample {i + 1}:")
        print(f"  Original (normalized): {orig}")
        print(f"  Back (normalized):     {back}")
        print(f"  SymPy:                 {sym}")
    else:
        print("✅ All roundtrips matched after canonical normalization.")

    # Warm roundtrip
    t2 = time.perf_counter()
    for expr in samples:
        _ = from_sympy(to_sympy(expr, lossless=True))
    t3 = time.perf_counter()
    warm_total = t3 - t2

    # Boolean-lowered
    t4 = time.perf_counter()
    for expr in samples:
        _ = to_sympy(expr, lossless=False)
    t5 = time.perf_counter()
    lowered_total = t5 - t4

    # Performance report
    print(f"Cold total:      {cold_total:.3f}s  ({n_samples / cold_total:,.1f} expr/s)")
    print(f"Warm total:      {warm_total:.3f}s  ({n_samples / warm_total:,.1f} expr/s)")
    print(f"Lowered total:   {lowered_total:.3f}s  ({n_samples / lowered_total:,.1f} expr/s)")
    print(f"Median op time:  {statistics.median([cold_total, warm_total, lowered_total]) * 1000 / n_samples:.3f} ms/op")
    print("======================================\n")


def test_benchmark_photon_sympy_bridge():
    benchmark_photon_sympy_bridge(n_samples=1000)


if __name__ == "__main__":
    benchmark_photon_sympy_bridge()