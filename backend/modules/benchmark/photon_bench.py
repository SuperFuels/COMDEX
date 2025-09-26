# benchmarks/photon_bench.py
"""
Photon Benchmark Suite
-----------------------
Compare Photon Rewriter vs Photon Compressor (basic + adv) vs Classical SymPy on:
  - Normalization speed
  - Expression size reduction (compression)
  - Gradient expansion scaling
  - Stress scaling (large N chains)
Results are exported to docs/rfc/photon_benchmarks.md
"""

import time
import sympy as sp
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


EXPRESSIONS_STRESS = {
    "add_chain_10": make_add_chain(10),
    "add_chain_50": make_add_chain(50),
    "add_chain_100": make_add_chain(100),
    "mul_chain_10": make_mul_chain(10),
    "mul_chain_50": make_mul_chain(50),
    "grad_add_10": make_grad_add(10),
    "grad_add_50": make_grad_add(50),
}


# --- Helpers ---
def bench_time(fn, expr_str, repeat=50):
    """Average execution time (ms) for fn(expr_str)."""
    start = time.perf_counter()
    for _ in range(repeat):
        fn(expr_str)
    elapsed = (time.perf_counter() - start) / repeat
    return elapsed * 1000  # ms


def expr_size(expr):
    """Rough complexity = number of nodes in SymPy tree."""
    return len(list(sp.preorder_traversal(expr)))


def run_set(expressions, label="Core"):
    rows = []
    for name, expr in expressions.items():
        # Photon raw
        t_photon = bench_time(rewriter.normalize, expr, repeat=100)
        norm = rewriter.normalize(expr)
        size_photon = expr_size(norm)

        # PhotonC basic
        t_basic = bench_time(lambda e: compressor.normalize_compressed(expr, mode="basic"), expr, repeat=100)
        normB = compressor.normalize_compressed(expr, mode="basic")
        size_basic = expr_size(normB)

        # PhotonC adv
        t_adv = bench_time(lambda e: compressor.normalize_compressed(expr, mode="advanced"), expr, repeat=100)
        normA = compressor.normalize_compressed(expr, mode="advanced")
        size_adv = expr_size(normA)

        # SymPy baseline
        expr_sym = sp.sympify(expr.replace("⊕", "+").replace("⊗", "*"))
        t_sympy = bench_time(lambda e: sp.simplify(expr_sym), expr, repeat=100)
        simp = sp.simplify(expr_sym)
        size_sympy = expr_size(simp)

        # Metrics
        comp_raw = (size_sympy - size_photon) / max(size_sympy, 1)
        comp_basic = (size_sympy - size_basic) / max(size_sympy, 1)
        comp_adv = (size_sympy - size_adv) / max(size_sympy, 1)

        speed_raw = t_photon / max(t_sympy, 1e-9)
        speed_basic = t_basic / max(t_sympy, 1e-9)
        speed_adv = t_adv / max(t_sympy, 1e-9)

        print(
            f"[{label}/{name:<12}] "
            f"Photon={size_photon}, Basic={size_basic}, Adv={size_adv}, SymPy={size_sympy}, "
            f"CompRaw={comp_raw:.2%}, CompBasic={comp_basic:.2%}, CompAdv={comp_adv:.2%}, "
            f"t_photon={t_photon:.2f}ms, t_basic={t_basic:.2f}ms, t_adv={t_adv:.2f}ms, t_sympy={t_sympy:.2f}ms"
        )

        rows.append(
            dict(
                expr=name,
                t_photon=t_photon,
                t_basic=t_basic,
                t_adv=t_adv,
                t_sympy=t_sympy,
                size_photon=size_photon,
                size_basic=size_basic,
                size_adv=size_adv,
                size_sympy=size_sympy,
                comp_raw=comp_raw,
                comp_basic=comp_basic,
                comp_adv=comp_adv,
                speed_raw=speed_raw,
                speed_basic=speed_basic,
                speed_adv=speed_adv,
            )
        )
    return rows


# --- Markdown Export ---
def export_markdown(rows_core, rows_stress, path="docs/rfc/photon_benchmarks.md"):
    def table(rows, title):
        lines = [
            f"## {title} — Raw Numbers",
            "",
            "| Expr | Photon ms | PhotonC Basic ms | PhotonC Adv ms | SymPy ms | "
            "Photon size | Basic size | Adv size | SymPy size | CompRaw | CompBasic | CompAdv | "
            "SpeedRaw | SpeedBasic | SpeedAdv |",
            "|------|-----------|------------------|----------------|----------|"
            "-------------|------------|----------|------------|---------|-----------|---------|"
            "----------|-----------|----------|",
        ]
        for r in rows:
            lines.append(
                f"| {r['expr']} | {r['t_photon']:.3f} | {r['t_basic']:.3f} | {r['t_adv']:.3f} | {r['t_sympy']:.3f} | "
                f"{r['size_photon']} | {r['size_basic']} | {r['size_adv']} | {r['size_sympy']} | "
                f"{r['comp_raw']:.2%} | {r['comp_basic']:.2%} | {r['comp_adv']:.2%} | "
                f"{r['speed_raw']:.2f}× | {r['speed_basic']:.2f}× | {r['speed_adv']:.2f}× |"
            )
        return lines

    def emoji_table(rows, title):
        lines = [
            f"## {title} — Emoji View",
            "",
            "| Expr | 🕒 Speed Winner | 📦 Compression Winner | Notes |",
            "|------|----------------|------------------------|-------|",
        ]
        for r in rows:
            # Speed winner
            times = {
                "Photon": r["t_photon"],
                "Basic": r["t_basic"],
                "Adv": r["t_adv"],
                "SymPy": r["t_sympy"],
            }
            fastest = min(times, key=times.get)
            speed_win = f"🏆 {fastest} 🟢" if fastest != "SymPy" else "🏆 SymPy 🔴"

            # Compression winner
            sizes = {
                "Photon": r["size_photon"],
                "Basic": r["size_basic"],
                "Adv": r["size_adv"],
                "SymPy": r["size_sympy"],
            }
            smallest = min(sizes, key=sizes.get)
            comp_win = f"{smallest} 📉" if smallest != "SymPy" else "SymPy 📈"

            notes = []
            if r["comp_basic"] > r["comp_raw"]:
                notes.append("Basic compressed better")
            if r["comp_adv"] > r["comp_basic"]:
                notes.append("Adv compressed better")
            if r["t_basic"] < r["t_photon"]:
                notes.append("Basic faster")
            if r["t_adv"] < r["t_basic"]:
                notes.append("Adv faster")
            note_str = ", ".join(notes) if notes else "-"

            lines.append(f"| {r['expr']} | {speed_win} | {comp_win} | {note_str} |")
        return lines

    lines = ["# Photon Benchmarks", ""]
    lines += table(rows_core, "Core (small expressions)")
    lines.append("")
    lines += emoji_table(rows_core, "Core (small expressions)")
    lines.append("")
    lines += table(rows_stress, "Stress (large chains)")
    lines.append("")
    lines += emoji_table(rows_stress, "Stress (large chains)")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"📊 Benchmarks exported → {path}")


if __name__ == "__main__":
    rows_core = run_set(EXPRESSIONS_CORE, "Core")
    rows_stress = run_set(EXPRESSIONS_STRESS, "Stress")
    export_markdown(rows_core, rows_stress)