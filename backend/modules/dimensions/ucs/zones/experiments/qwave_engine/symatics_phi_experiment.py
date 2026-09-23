from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

import numpy as np

GOLDEN = 1.61803398875
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


def _row_label(row: dict, idx: int) -> str:
    phi = row.get("phi_hint", row.get("phi"))
    harm = row.get("harmonics", row.get("harmonic", "unknown"))
    if isinstance(harm, list):
        harm = "-".join(str(x) for x in harm)
    return f"row_{idx:03d}_phi_{float(phi):.6f}_harm_{harm}"


def _pickup_trace(row: dict) -> np.ndarray:
    trace = row.get("pickup_trace", [])
    return np.asarray(trace, dtype=float)


def _hann(x: np.ndarray) -> np.ndarray:
    if x.size == 0:
        return x
    return x * np.hanning(x.size)


def _dominant_peaks_fft(x: np.ndarray, k: int = 8) -> list[tuple[int, float]]:
    if x.size < 16:
        return []
    x = x - np.mean(x)
    fft = np.fft.rfft(_hann(x))
    mag = np.abs(fft)
    if mag.size:
        mag[0] = 0.0
    idx = np.argsort(mag)[::-1]
    out: list[tuple[int, float]] = []
    for i in idx[:k]:
        if mag[i] > 0:
            out.append((int(i), float(mag[i])))
    return out


def _coherence_from_top_peaks(peaks: list[tuple[int, float]]) -> float:
    if len(peaks) < 2:
        return 0.0
    mags = np.asarray([p[1] for p in peaks[:2]], dtype=float)
    if mags.sum() <= 0:
        return 0.0
    return float(mags.max() / mags.sum())


def _phi_grid(center: float, step: float, count: int) -> list[float]:
    half = count // 2
    return [center + (i - half) * step for i in range(count)]


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
        *[f"{x:.7f}" for x in phis],
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
    phis = _phi_grid(args.center_phi, args.phi_step, args.phi_count)
    out_path = _run_capture(
        phis=phis,
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
        if trace.size < 16:
            continue

        peaks = _dominant_peaks_fft(trace, k=8)
        if len(peaks) < 2:
            continue

        f1, _ = peaks[0]
        f2, _ = peaks[1]
        ratio = max(f1, f2) / max(1, min(f1, f2))
        err = abs(ratio - GOLDEN)
        coherence = _coherence_from_top_peaks(peaks)
        drift = float(row.get("drift", 0.0))
        phi = float(row.get("phi_hint", row.get("phi", math.nan)))
        pickup = float(row.get("pickup_mean", 0.0))

        if drift > args.max_drift:
            continue
        if coherence < args.min_coherence:
            continue

        results.append(
            {
                "label": _row_label(row, idx),
                "phi": phi,
                "ratio": ratio,
                "err": err,
                "peaks": (f1, f2),
                "coherence": coherence,
                "pickup": pickup,
                "drift": drift,
                "harmonics": row.get("harmonics", row.get("harmonic")),
                "alpha": row.get("alpha"),
                "nu": row.get("nu"),
            }
        )

    results.sort(key=lambda r: (r["err"], -r["coherence"], r["drift"]))

    print("\n=== PHI EXPERIMENT ===\n")
    print(f"capture: {out_path}")
    print(f"tested rows: {len(rows)}")
    print(f"filtered rows: {len(results)}")
    print(f"target golden ratio: {GOLDEN:.11f}\n")

    if not results:
        print("No rows passed filters.")
        return

    for r in results[: args.top_k]:
        print(
            f"{r['label']} | phi={r['phi']:.7f} | ratio={r['ratio']:.6f} | "
            f"err={r['err']:.6f} | peaks={r['peaks'][0]},{r['peaks'][1]} | "
            f"coherence={r['coherence']:.6f} | pickup={r['pickup']:.6f} | drift={r['drift']:.6f}"
        )

    best = results[0]
    print("\n--- BEST PHI CANDIDATE ---")
    print(
        f"{best['label']} | phi={best['phi']:.7f} | ratio={best['ratio']:.6f} | "
        f"err={best['err']:.6f} | peaks={best['peaks'][0]},{best['peaks'][1]} | "
        f"coherence={best['coherence']:.6f}"
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--center-phi", type=float, default=3.1415930)
    ap.add_argument("--phi-step", type=float, default=0.0000002)
    ap.add_argument("--phi-count", type=int, default=17)
    ap.add_argument("--harmonics", nargs="+", default=["1", "2", "3", "1,2", "1,3", "2,3", "1,2,3"])
    ap.add_argument("--alphas", nargs="+", type=float, default=[0.08])
    ap.add_argument("--nus", nargs="+", type=float, default=[0.02])
    ap.add_argument("--ticks", type=int, default=512)
    ap.add_argument("--trace-max-points", type=int, default=512)
    ap.add_argument("--warmup-ticks", type=int, default=256)
    ap.add_argument("--max-drift", type=float, default=0.02)
    ap.add_argument("--min-coherence", type=float, default=0.95)
    ap.add_argument("--top-k", type=int, default=10)
    run(ap.parse_args())