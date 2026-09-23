from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

import numpy as np

HERE = Path(__file__).resolve().parent
SWEEP_SCRIPT = HERE / "manual_symatics_capture_sweep.py"


def _loads_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _harm_to_text(harm: object) -> str:
    if isinstance(harm, list):
        return "-".join(str(x) for x in harm)
    return str(harm)


def _row_label(row: dict, idx: int) -> str:
    phi = row.get("phi_hint", row.get("phi"))
    harm = row.get("harmonics", row.get("harmonic", "unknown"))
    return f"row_{idx:03d}_phi_{float(phi):.6f}_harm_{_harm_to_text(harm)}"


def _pickup_trace(row: dict) -> np.ndarray:
    return np.asarray(row.get("pickup_trace", []), dtype=float)


def _coherence_from_trace(trace: np.ndarray) -> float:
    if trace.size < 16:
        return 0.0
    x = trace - np.mean(trace)
    fft = np.fft.rfft(x * np.hanning(x.size))
    mag = np.abs(fft)
    if mag.size:
        mag[0] = 0.0
    idx = np.argsort(mag)[::-1]
    mags = mag[idx[:2]]
    if mags.sum() <= 0:
        return 0.0
    return float(mags.max() / mags.sum())


def _smooth_abs_envelope(trace: np.ndarray, window: int) -> np.ndarray:
    x = np.abs(trace.astype(float))
    window = max(3, int(window))
    if window % 2 == 0:
        window += 1
    if x.size < window:
        return x.copy()
    kernel = np.ones(window, dtype=float) / float(window)
    return np.convolve(x, kernel, mode="same")


def _find_decay_segment(
    env: np.ndarray,
    min_segment_len: int,
    monotone_tol: float,
) -> tuple[int, int]:
    """
    Find the longest approximately monotone-decaying segment in the envelope.
    """
    n = env.size
    if n < min_segment_len:
        return 0, 0

    best = (0, 0)
    i = 0
    while i < n - 1:
        j = i + 1
        while j < n:
            if env[j] <= env[j - 1] + monotone_tol:
                j += 1
            else:
                break
        if (j - i) >= min_segment_len and (j - i) > (best[1] - best[0]):
            best = (i, j)
        i = max(i + 1, j)

    return best


def _exp_fit(segment: np.ndarray) -> tuple[float, float, float]:
    if segment.size < 20:
        return float("inf"), -1.0, 0.0

    y = np.asarray(segment, dtype=float)
    y = y - np.min(y) + 1e-9
    t = np.arange(y.size, dtype=float)

    logy = np.log(y)
    slope, intercept = np.polyfit(t, logy, 1)
    tau = -1.0 / slope if slope < 0 else float("inf")

    y_fit = np.exp(intercept + slope * t)
    ss_res = float(np.sum((y - y_fit) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else -1.0
    return tau, r2, slope


def _run_capture(
    phis: Iterable[float],
    harmonics: list[str],
    alphas: list[float],
    nus: list[float],
    ticks: int,
    trace_max_points: int,
    warmup_ticks: int,
) -> Path:
    cmd = [
        sys.executable,
        str(SWEEP_SCRIPT),
        "--safe-mode",
        "--quiet-sim",
        "--store-traces",
        "--trace-max-points",
        str(trace_max_points),
        "--warmup-ticks",
        str(warmup_ticks),
        "--phis",
        *[f"{x:.9f}" for x in phis],
        "--harmonics",
        *harmonics,
        "--alphas",
        *[f"{x:.6f}" for x in alphas],
        "--nus",
        *[f"{x:.6f}" for x in nus],
        "--ticks",
        str(ticks),
    ]
    env = dict(os.environ)
    env.setdefault("PYTHONPATH", ".")
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, check=True)
    match = re.search(r"Wrote:\s*(.+\.jsonl)", proc.stdout)
    if not match:
        raise RuntimeError(f"Could not locate output path in capture stdout:\n{proc.stdout}")
    return Path(match.group(1).strip())


def run(args: argparse.Namespace) -> None:
    if args.input:
        out_path = Path(args.input)
    else:
        out_path = _run_capture(
            phis=args.phis,
            harmonics=args.harmonics,
            alphas=args.alphas,
            nus=args.nus,
            ticks=args.ticks,
            trace_max_points=args.trace_max_points,
            warmup_ticks=args.warmup_ticks,
        )

    rows = _loads_jsonl(out_path)

    results: list[dict] = []
    for idx, row in enumerate(rows, start=1):
        trace = _pickup_trace(row)
        if trace.size < 64:
            continue

        coherence = _coherence_from_trace(trace)
        if coherence < args.min_coherence:
            continue

        drift = float(row.get("drift", 0.0))
        if drift > args.max_drift:
            continue

        env = _smooth_abs_envelope(trace, args.envelope_window)
        seg_lo, seg_hi = _find_decay_segment(
            env=env,
            min_segment_len=args.min_segment_len,
            monotone_tol=args.monotone_tol,
        )
        if seg_hi <= seg_lo:
            continue

        segment = env[seg_lo:seg_hi]
        tau_env, env_r2, slope = _exp_fit(segment)

        results.append(
            {
                "label": _row_label(row, idx),
                "phi": float(row.get("phi_hint", row.get("phi", math.nan))),
                "harm": _harm_to_text(row.get("harmonics", row.get("harmonic", "unknown"))),
                "tau_env": tau_env,
                "env_r2": env_r2,
                "slope": slope,
                "seg_lo": seg_lo,
                "seg_hi": seg_hi,
                "seg_len": int(seg_hi - seg_lo),
                "coherence": coherence,
                "drift": drift,
                "pickup": float(row.get("pickup_mean", row.get("pickup", 0.0))),
                "alpha": float(row.get("alpha", math.nan)),
                "nu": float(row.get("nu", math.nan)),
            }
        )

    results.sort(
        key=lambda r: (
            -r["env_r2"],
            r["tau_env"] if math.isfinite(r["tau_env"]) else float("inf"),
            r["drift"],
        )
    )

    print("\n=== E EXPERIMENT ===\n")
    print("protocol: natural envelope decay-fit")
    print(f"capture: {out_path}")
    print(f"tested rows: {len(rows)}")
    print(f"filtered rows: {len(results)}\n")

    if not results:
        print("No rows passed filters.")
        return

    for r in results[: args.top_k]:
        tau_txt = f"{r['tau_env']:.3f}" if math.isfinite(r["tau_env"]) else "inf"
        print(
            f"{r['label']} | phi={r['phi']:.9f} | harm={r['harm']} | "
            f"alpha={r['alpha']:.6f} | tau_env={tau_txt} | "
            f"env_r2={r['env_r2']:.6f} | slope={r['slope']:.6f} | "
            f"seg=[{r['seg_lo']},{r['seg_hi']}) len={r['seg_len']} | "
            f"coherence={r['coherence']:.6f} | drift={r['drift']:.6f}"
        )

    best = results[0]
    tau_txt = f"{best['tau_env']:.3f}" if math.isfinite(best["tau_env"]) else "inf"
    print("\n--- BEST E CANDIDATE ---")
    print(
        f"{best['label']} | phi={best['phi']:.9f} | harm={best['harm']} | "
        f"alpha={best['alpha']:.6f} | tau_env={tau_txt} | "
        f"env_r2={best['env_r2']:.6f} | slope={best['slope']:.6f} | "
        f"coherence={best['coherence']:.6f}"
    )

    mean_env_r2 = sum(r["env_r2"] for r in results) / len(results)
    print("\n--- SUMMARY ---")
    print(f"mean_env_r2          : {mean_env_r2:.6f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="", help="Existing sweep JSONL to analyse")
    ap.add_argument("--phis", nargs="+", type=float, default=[3.1415928, 3.1415930, 3.1415932, 3.1415934])
    ap.add_argument("--harmonics", nargs="+", default=["1", "2", "3"])
    ap.add_argument("--alphas", nargs="+", type=float, default=[0.04, 0.06, 0.08, 0.10, 0.12])
    ap.add_argument("--nus", nargs="+", type=float, default=[0.01, 0.02, 0.03])
    ap.add_argument("--ticks", type=int, default=1024)
    ap.add_argument("--trace-max-points", type=int, default=1024)
    ap.add_argument("--warmup-ticks", type=int, default=256)
    ap.add_argument("--min-coherence", type=float, default=0.26)
    ap.add_argument("--max-drift", type=float, default=0.02)
    ap.add_argument("--envelope-window", type=int, default=15)
    ap.add_argument("--min-segment-len", type=int, default=48)
    ap.add_argument("--monotone-tol", type=float, default=5e-4)
    ap.add_argument("--top-k", type=int, default=10)
    run(ap.parse_args())