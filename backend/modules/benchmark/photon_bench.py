# benchmarks/photon_bench.py
"""
Photon Benchmark Suite
-----------------------
Compare Photon Rewriter vs Photon Compressor (basic + adv) vs Classical SymPy on:
  - Normalization speed
  - Expression size reduction (compression)
  - Gradient expansion scaling
  - Stress scaling (large N chains)

Results:
  - Markdown -> docs/rfc/photon_benchmarks.md
  - JSON     -> docs/rfc/photon_benchmarks.json
  - CSV      -> docs/rfc/photon_benchmarks.csv
"""

import time
import statistics
import sympy as sp
import json
import csv
import platform
import datetime
from backend.photon.rewriter import rewriter
from backend.photon.compressor import compressor

# --- Sample Expressions (Core small ones) ---
x, y, z = sp.symbols("x y z")

EXPRESSIONS_CORE = {
    "add_chain": "x ⊕ y ⊕ z ⊕ (x ⊕ y)",
    "mul_chain": "(x ⊗ y ⊗ z) ⊗ (x ⊗ y)",
    "grad_add": "∇(x ⊕ y ⊕ z)",
    "grad_mul": "∇((x ⊕ y) ⊗ z)",
    "nested": "∇(((x ⊕ y) ⊗ (z ⊕ x)) ⊗ y)",
}


# --- Stress Expressions (auto-generated) ---
def make_add_chain(n):
    return " ⊕ ".join([f"x{i}" for i in range(n)])


def make_mul_chain(n):
    return " ⊗ ".join([f"x{i}" for i in range(n)])


def make_grad_add(n):
    return f"∇({' ⊕ '.join([f'x{i}' for i in range(n)])})"


def make_repeat_add(n):
    return " ⊕ ".join(["x"] * n)


def make_repeat_mul(n):
    return " ⊗ ".join(["x"] * n)


def make_grad_repeat_add(n):
    return f"∇({' ⊕ '.join(['x'] * n)})"


def make_grad_repeat_mul(n):
    return f"∇({' ⊗ '.join(['x'] * n)})"


EXPRESSIONS_STRESS = {
    # distinct variable chains
    "add_chain_10": make_add_chain(10),
    "add_chain_50": make_add_chain(50),
    "add_chain_100": make_add_chain(100),
    "mul_chain_10": make_mul_chain(10),
    "mul_chain_50": make_mul_chain(50),
    "grad_add_10": make_grad_add(10),
    "grad_add_50": make_grad_add(50),

    # repeated-variable chains (tests factoring)
    "repeat_add_10": make_repeat_add(10),
    "repeat_add_50": make_repeat_add(50),
    "repeat_add_100": make_repeat_add(100),
    "repeat_mul_10": make_repeat_mul(10),
    "repeat_mul_50": make_repeat_mul(50),
    "repeat_mul_100": make_repeat_mul(100),

    # gradient + repeats (hardest cases)
    "grad_repeat_add_10": make_grad_repeat_add(10),
    "grad_repeat_add_50": make_grad_repeat_add(50),
    "grad_repeat_mul_10": make_grad_repeat_mul(10),
    "grad_repeat_mul_50": make_grad_repeat_mul(50),
}


# --- Helpers ---
def bench_time(fn, expr_str, repeat=50, warmup=5):
    """Return mean, median, and stddev (ms) for fn(expr_str)."""
    for _ in range(warmup):
        fn(expr_str)
    times = []
    for _ in range(repeat):
        start = time.perf_counter()
        fn(expr_str)
        times.append((time.perf_counter() - start) * 1000)
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stddev": statistics.stdev(times) if len(times) > 1 else 0.0,
    }


def expr_size(expr):
    """Rough complexity = number of nodes in SymPy tree."""
    return len(list(sp.preorder_traversal(expr)))


def run_set(expressions, label="Core"):
    rows = []
    for name, expr in expressions.items():
        try:
            # Photon raw
            t_photon = bench_time(rewriter.normalize, expr, repeat=50)
            norm = rewriter.normalize(expr)
            size_photon = expr_size(norm)

            # PhotonC basic
            t_basic = bench_time(lambda e: compressor.normalize_compressed(e, mode="basic"), expr, repeat=50)
            normB = compressor.normalize_compressed(expr, mode="basic")
            size_basic = expr_size(normB)

            # PhotonC adv
            t_adv = bench_time(lambda e: compressor.normalize_compressed(e, mode="advanced"), expr, repeat=50)
            normA = compressor.normalize_compressed(expr, mode="advanced")
            size_adv = expr_size(normA)

            # SymPy baseline
            expr_sym = sp.sympify(expr.replace("⊕", "+").replace("⊗", "*"))
            t_sympy = bench_time(lambda e: sp.simplify(expr_sym), expr, repeat=50)
            simp = sp.simplify(expr_sym)
            size_sympy = expr_size(simp)

            # Metrics
            comp_raw = (size_sympy - size_photon) / max(size_sympy, 1)
            comp_basic = (size_sympy - size_basic) / max(size_sympy, 1)
            comp_adv = (size_sympy - size_adv) / max(size_sympy, 1)

            speed_raw = t_photon["median"] / max(t_sympy["median"], 1e-9)
            speed_basic = t_basic["median"] / max(t_sympy["median"], 1e-9)
            speed_adv = t_adv["median"] / max(t_sympy["median"], 1e-9)

            # Log
            print(
                f"[{label}/{name:<18}] "
                f"Photon={size_photon}, Basic={size_basic}, Adv={size_adv}, SymPy={size_sympy}, "
                f"t_photon={t_photon['median']:.2f}ms, t_basic={t_basic['median']:.2f}ms, "
                f"t_adv={t_adv['median']:.2f}ms, t_sympy={t_sympy['median']:.2f}ms"
            )

            rows.append(
                dict(
                    expr=name,
                    size_photon=size_photon,
                    size_basic=size_basic,
                    size_adv=size_adv,
                    size_sympy=size_sympy,
                    t_photon=t_photon,
                    t_basic=t_basic,
                    t_adv=t_adv,
                    t_sympy=t_sympy,
                    comp_raw=comp_raw,
                    comp_basic=comp_basic,
                    comp_adv=comp_adv,
                    speed_raw=speed_raw,
                    speed_basic=speed_basic,
                    speed_adv=speed_adv,
                )
            )
        except Exception as run_err:
            print(f"⚠️ Benchmark failed for {label}/{name}: {run_err}")
    return rows


# --- Exporters ---
def export_markdown(rows_core, rows_stress, path="docs/rfc/photon_benchmarks.md"):
    meta = [
        "# Photon Benchmarks",
        f"_Generated: {datetime.datetime.now().isoformat()}_",
        f"_Python: {platform.python_version()} / {platform.system()} {platform.machine()}_",
        ""
    ]

    def table(rows, title):
        lines = [
            f"## {title} - Raw Numbers",
            "",
            "| Expr | Photon ms | PhotonC Basic ms | PhotonC Adv ms | SymPy ms | "
            "Photon size | Basic size | Adv size | SymPy size | "
            "CompRaw | CompBasic | CompAdv | SpeedRaw | SpeedBasic | SpeedAdv |",
            "|------|-----------|------------------|----------------|----------|"
            "-------------|------------|----------|------------|---------|-----------|---------|----------|-----------|----------|",
        ]
        for r in rows:
            lines.append(
                f"| {r['expr']} | {r['t_photon']['median']:.3f} | {r['t_basic']['median']:.3f} | {r['t_adv']['median']:.3f} | {r['t_sympy']['median']:.3f} | "
                f"{r['size_photon']} | {r['size_basic']} | {r['size_adv']} | {r['size_sympy']} | "
                f"{r['comp_raw']:.2%} | {r['comp_basic']:.2%} | {r['comp_adv']:.2%} | "
                f"{r['speed_raw']:.2f}* | {r['speed_basic']:.2f}* | {r['speed_adv']:.2f}* |"
            )
        return lines

    lines = meta
    lines += table(rows_core, "Core (small expressions)")
    lines.append("")
    lines += table(rows_stress, "Stress (large chains)")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"📊 Benchmarks exported -> {path}")


def export_json(rows_core, rows_stress, path="docs/rfc/photon_benchmarks.json"):
    data = {
        "meta": {
            "generated": datetime.datetime.now().isoformat(),
            "python": platform.python_version(),
            "system": f"{platform.system()} {platform.machine()}",
        },
        "core": rows_core,
        "stress": rows_stress,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"📊 JSON exported -> {path}")


def export_csv(rows_core, rows_stress, path="docs/rfc/photon_benchmarks.csv"):
    keys = [
        "expr", "size_photon", "size_basic", "size_adv", "size_sympy",
        "comp_raw", "comp_basic", "comp_adv",
        "speed_raw", "speed_basic", "speed_adv",
        "t_photon", "t_basic", "t_adv", "t_sympy"
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(keys)
        for rowset in (rows_core, rows_stress):
            for r in rowset:
                writer.writerow([
                    r["expr"],
                    r["size_photon"], r["size_basic"], r["size_adv"], r["size_sympy"],
                    r["comp_raw"], r["comp_basic"], r["comp_adv"],
                    r["speed_raw"], r["speed_basic"], r["speed_adv"],
                    r["t_photon"]["median"], r["t_basic"]["median"], r["t_adv"]["median"], r["t_sympy"]["median"]
                ])
    print(f"📊 CSV exported -> {path}")


if __name__ == "__main__":
    rows_core = run_set(EXPRESSIONS_CORE, "Core")
    rows_stress = run_set(EXPRESSIONS_STRESS, "Stress")
    export_markdown(rows_core, rows_stress)
    export_json(rows_core, rows_stress)
    export_csv(rows_core, rows_stress)