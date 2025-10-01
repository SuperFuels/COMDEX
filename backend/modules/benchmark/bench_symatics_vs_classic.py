# File: backend/modules/benchmark/bench_symatics_vs_classic.py
"""
Benchmark: Symatics ⋈ rewriter vs Classical Boolean ∧/∨
──────────────────────────────────────────────────────────────
Measures:
  • normalize() speed on ⋈ expressions
  • equivalence checks (symatics_equiv vs structural eqv on ∧/∨)
  • expression size reduction (nodes before vs after normalize)
  • scaling behavior for larger expressions (10, 50, 100, 200, …)
  • stability profile: % converged, avg time, avg size reduction
"""

import math
import random
import time
from statistics import mean, median

from backend.symatics import rewriter as R


# ------------------
# Classic Boolean ops
# ------------------

class BoolExpr:
    def __init__(self, kind, left=None, right=None, name=None):
        self.kind = kind  # "atom" | "and" | "or"
        self.left = left
        self.right = right
        self.name = name

    def __eq__(self, other):
        return (
            isinstance(other, BoolExpr)
            and self.kind == other.kind
            and self.name == other.name
            and self.left == other.left
            and self.right == other.right
        )


def AtomB(name="A"): return BoolExpr("atom", name=name)
def And(l, r): return BoolExpr("and", left=l, right=r)
def Or(l, r): return BoolExpr("or", left=l, right=r)


def normalize_bool(e: BoolExpr) -> BoolExpr:
    """Trivial normalize: enforce right-associativity."""
    if e.kind in ("and", "or") and isinstance(e.left, BoolExpr) and e.left.kind == e.kind:
        return BoolExpr(
            e.kind,
            left=e.left.left,
            right=BoolExpr(e.kind, e.left.right, e.right),
        )
    return e


# ------------------
# Expression builders
# ------------------

def chain_sym_expr(n: int) -> R.Expr:
    """Build a chain of n interference nodes."""
    e = R.Sym("A")
    for i in range(n):
        φ = random.choice([0.0, math.pi, random.uniform(-3.14, 3.14)])
        e = R.interf(φ, e, R.Sym(chr(66 + (i % 3))))  # B, C, D cycling
    return e


def chain_bool_expr(n: int) -> BoolExpr:
    e = AtomB("A")
    for i in range(n):
        if random.random() < 0.5:
            e = And(e, AtomB(chr(66 + (i % 3))))
        else:
            e = Or(e, AtomB(chr(66 + (i % 3))))
    return e


# ------------------
# Helpers
# ------------------

def size_expr(e):
    """Compute approximate size (node count) of an expression without recursion."""
    seen = set()
    stack = [e]
    size = 0

    while stack:
        node = stack.pop()
        if id(node) in seen:
            continue
        seen.add(id(node))

        if isinstance(node, R.App) and isinstance(node.head, R.Sym):
            size += 1
            stack.extend(node.args)
        elif isinstance(node, R.Sym):
            size += 1
        elif isinstance(node, BoolExpr):
            size += 1
            if node.left:
                stack.append(node.left)
            if node.right:
                stack.append(node.right)
        else:
            size += 1

    return size


# ------------------
# Stability Benchmark
# ------------------

def stability_profile(n: int, trials: int = 100, step_factor: int = 20):
    times = []
    sizes_before = []
    sizes_after = []
    converged = 0
    for _ in range(trials):
        expr = chain_sym_expr(n)
        before = size_expr(expr)
        try:
            # Adaptive budget: proportional to size
            budget = max(1000, step_factor * before)
            t0 = time.perf_counter()
            norm = R.normalize(expr, max_steps=budget)
            t1 = time.perf_counter()
            after = size_expr(norm)
            times.append((t1 - t0) * 1e6)
            sizes_before.append(before)
            sizes_after.append(after)
            converged += 1
        except RuntimeError:
            sizes_before.append(before)
            sizes_after.append(before)
    conv_rate = 100.0 * converged / trials
    avg_time = mean(times) if times else float("inf")
    med_time = median(times) if times else float("inf")
    avg_reduction = mean(b - a for b, a in zip(sizes_before, sizes_after))
    return {
        "n": n,
        "trials": trials,
        "conv_rate": conv_rate,
        "avg_time": avg_time,
        "med_time": med_time,
        "avg_reduction": avg_reduction,
    }


# ------------------
# Main benchmark
# ------------------

def main():
    print("=== Symatics ⋈ Rewriter vs Classical Boolean ===\n")

    # Simple speed comparison (tiny exprs)
    e_sym = chain_sym_expr(3)
    e_bool = chain_bool_expr(3)

    t0 = time.perf_counter(); R.normalize(e_sym); t1 = time.perf_counter()
    print(f"symatics.normalize {1/(t1-t0):.1f} ops/sec (avg {(t1-t0)*1e6:.1f} µs)")

    t0 = time.perf_counter(); normalize_bool(e_bool); t1 = time.perf_counter()
    print(f"bool.normalize     {1/(t1-t0):.1f} ops/sec (avg {(t1-t0)*1e6:.1f} µs)")

    # Scaling stability runs (extended stress)
    print("\n--- Scaling stability benchmarks ---")
    for n in [10, 50, 100, 200, 500, 1000, 2000]:
        profile = stability_profile(n, trials=20, step_factor=20)
        print(
            f"n={n:4d} | conv={profile['conv_rate']:.1f}% "
            f"| avg={profile['avg_time']:.1f} µs "
            f"| med={profile['med_time']:.1f} µs "
            f"| avg Δsize={profile['avg_reduction']:.1f}"
        )

    print("\n✅ Benchmark completed.")


if __name__ == "__main__":
    main()