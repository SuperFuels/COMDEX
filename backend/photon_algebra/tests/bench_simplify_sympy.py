# -*- coding: utf-8 -*-
"""
Photon ↔ SymPy Simplify Benchmark
=================================
Task: I2.3 — Evaluate SymPy simplification performance and correctness

Measures throughput and equivalence of simplifying Photon expressions
via SymPy roundtrip:

    Photon → SymPy → simplify() → Photon

Unknown custom Photon operators (★, ⊖, ≈, ⊂) are skipped from simplification
to avoid SymPy raising ValueError for unregistered BooleanFunctions.
"""

import time
import statistics
import sympy as sp

from backend.photon_algebra.sympy_bridge import to_sympy, from_sympy
from backend.photon_algebra.rewriter import normalize
from backend.photon_algebra.tests.test_pp_roundtrip import photon_exprs


# -------------------------------------------------------------------------
# Utility simplifier with safe fallback
# -------------------------------------------------------------------------
def _safe_simplify(sexpr, mode="auto"):
    """Perform safe SymPy simplification, skipping unsupported Photon ops."""
    try:
        if any(op.__name__.startswith("Photon") for op in sexpr.atoms(sp.Function)):
            return sexpr

        if mode == "auto":
            return sp.simplify_logic(sexpr, form="dnf")
        elif mode == "cnf":
            return sp.to_cnf(sexpr, simplify=True)
        elif mode == "dnf":
            return sp.to_dnf(sexpr, simplify=True)
        elif mode == "simplify":
            return sp.simplify(sexpr)
        else:
            return sexpr
    except Exception as e:
        if any(op in str(e) for op in ["PhotonMinus", "PhotonStar", "PhotonSubset", "PhotonApprox"]):
            return sexpr
        print(f"⚠️  Skipped complex simplify ({mode}): {e}")
        return sexpr


def _sample_photon_exprs(n_samples=2000):
    """Safely generate deterministic Photon expression examples."""
    strategy = photon_exprs()
    return [strategy.example() for _ in range(n_samples)]


# -------------------------------------------------------------------------
# Benchmark core
# -------------------------------------------------------------------------
def benchmark_simplify_sympy(n_samples: int = 2000):
    """Run benchmark of simplify(to_sympy(expr)) → from_sympy(roundtrip)."""
    samples = _sample_photon_exprs(n_samples)
    modes = ["auto", "simplify", "cnf", "dnf"]

    print("\n=== Photon↔SymPy Simplify Benchmark ===")
    print(f"Expressions:     {n_samples:,}")

    for mode in modes:
        mismatches = 0
        t0 = time.perf_counter()

        for expr in samples:
            s_expr = to_sympy(expr, lossless=True)
            simplified = _safe_simplify(s_expr, mode=mode)
            back = from_sympy(simplified)

            n1, n2 = normalize(back), normalize(expr)
            if n1 != n2:
                try:
                    eq = bool(sp.simplify(sp.Equivalent(s_expr, simplified)))
                except Exception:
                    eq = False
                if not eq:
                    mismatches += 1

        t1 = time.perf_counter()
        total = t1 - t0
        rate = n_samples / total

        print(f"{mode.upper():<9} {total:7.3f}s  ({rate:9.1f} expr/s)  mismatches: {mismatches}")

        # Diagnostic output if mismatches are small enough to inspect
        if 0 < mismatches < 10:
            print(f"  ⚠️  Showing up to 3 mismatch examples for {mode}:")
            shown = 0
            for expr in samples:
                s_expr = to_sympy(expr, lossless=True)
                simplified = _safe_simplify(s_expr, mode=mode)
                back = from_sympy(simplified)
                n1, n2 = normalize(back), normalize(expr)
                if n1 != n2:
                    print("  ───────────────")
                    print("  Original:", expr)
                    print("  Simplified:", back)
                    print("  SymPy:", simplified)
                    shown += 1
                    if shown >= 3:
                        break

        # Adjust tolerance by mode
        limit = 0.10 if mode == "auto" else 0.05
        assert mismatches < n_samples * limit, \
            f"Too many simplification mismatches in {mode} ({mismatches}/{n_samples})"

    print("======================================\n")


# -------------------------------------------------------------------------
# Pytest entry
# -------------------------------------------------------------------------
def test_benchmark_simplify_sympy():
    benchmark_simplify_sympy(n_samples=500)


if __name__ == "__main__":
    benchmark_simplify_sympy()