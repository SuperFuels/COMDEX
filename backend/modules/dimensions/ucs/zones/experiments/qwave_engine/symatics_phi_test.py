from __future__ import annotations

import argparse
from symatics_test_common import (
    dominant_peaks_fft,
    get_pickup_trace,
    load_traces_from_jsonl,
    row_label,
    row_phi,
)

GOLDEN = 1.61803398875


def run(path: str):
    rows = load_traces_from_jsonl(path)

    print("\n=== PHI TEST ===\n")

    ranked = []

    for r in rows:
        trace = get_pickup_trace(r)
        peaks = dominant_peaks_fft(trace, k=5)

        if len(peaks) < 2:
            continue

        f1, _ = peaks[0]
        f2, _ = peaks[1]

        lo = max(1, min(f1, f2))
        hi = max(f1, f2)
        ratio = hi / lo
        err = abs(ratio - GOLDEN)

        ranked.append((err, row_label(r), row_phi(r), lo, hi, ratio))

    ranked.sort(key=lambda x: x[0])

    for err, label, phi, lo, hi, ratio in ranked:
        print(
            f"{label} | phi={phi:.9f} | "
            f"ratio={ratio:.6f} | err={err:.6f} | peaks=({lo},{hi})"
        )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    args = ap.parse_args()
    run(args.input)