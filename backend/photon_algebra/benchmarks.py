# backend/photon_algebra/benchmarks.py
"""
Photon Algebra Benchmarks (P11)
-------------------------------
Compare Photon vs. Classical (Boolean-like) algebra.

Metrics:
- Ops/sec: normalize() throughput on random expressions
- Compression: raw_expr_size / normalized_size
"""

import time
import random
import statistics
from typing import Any, Dict
from datetime import datetime

from backend.photon_algebra import core, rewriter


def random_expr(depth=3, symbols=("a", "b", "c", "d")) -> Dict[str, Any]:
    """Generate a random photon expression tree."""
    if depth == 0 or random.random() < 0.3:
        return random.choice(symbols)
    op = random.choice(["⊕", "⊗", "⊖", "¬"])
    if op == "¬":
        return {"op": "¬", "state": random_expr(depth - 1, symbols)}
    else:
        return {"op": op, "states": [
            random_expr(depth - 1, symbols),
            random_expr(depth - 1, symbols),
        ]}


def expr_size(expr: Any) -> int:
    """Count nodes in an expression tree."""
    if isinstance(expr, str):
        return 1
    if isinstance(expr, dict):
        if "state" in expr:
            return 1 + expr_size(expr["state"])
        if "states" in expr:
            return 1 + sum(expr_size(s) for s in expr["states"])
    return 1


def benchmark_ops(n=1000, depth=4):
    exprs = [random_expr(depth) for _ in range(n)]

    raw_sizes = [expr_size(e) for e in exprs]

    t0 = time.time()
    normalized = [rewriter.normalize(e) for e in exprs]
    t1 = time.time()

    norm_sizes = [expr_size(e) for e in normalized]

    ops_sec = n / (t1 - t0)
    compression = statistics.mean(r / n for r, n in zip(raw_sizes, norm_sizes) if n > 0)

    return {
        "count": n,
        "ops_sec": round(ops_sec, 2),
        "avg_raw_size": round(statistics.mean(raw_sizes), 2),
        "avg_norm_size": round(statistics.mean(norm_sizes), 2),
        "avg_compression": round(compression, 3),
    }


if __name__ == "__main__":
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"### Run: {now}\n")
    print("⚡ Photon Algebra Benchmark")
    result = benchmark_ops(n=5000, depth=5)
    for k, v in result.items():
        print(f"{k:>15}: {v}")
    print("\n---")