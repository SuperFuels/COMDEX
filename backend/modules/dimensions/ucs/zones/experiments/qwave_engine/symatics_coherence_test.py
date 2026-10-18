from __future__ import annotations

import argparse
from symatics_test_common import (
    load_traces_from_jsonl,
    row_label,
    row_phi,
    get_pickup_trace,
    phase_coherence,
    dominant_peaks_fft,
)


def run(path: str, min_coherence: float) -> None:
    rows = load_traces_from_jsonl(path)

    print("\n=== COHERENCE / INFORMATION TEST ===\n")

    scored = []
    for idx, r in enumerate(rows):
        trace = get_pickup_trace(r)
        if trace.size < 16:
            continue

        coh = phase_coherence(trace)
        peaks = dominant_peaks_fft(trace, k=3)
        peak_txt = ",".join(str(p[0]) for p in peaks[:2]) if peaks else "-"

        scored.append((coh, row_label(r, idx), row_phi(r), peak_txt))

    scored.sort(reverse=True, key=lambda x: x[0])

    passed = False
    for coh, label, phi, peak_txt in scored:
        if coh >= min_coherence:
            passed = True
        print(
            f"{label} | phi={phi:.9f} | "
            f"coherence={coh:.6f} | peaks={peak_txt}"
        )

    print("\n--- SUMMARY ---")
    print(f"tested rows   : {len(scored)}")
    print(f"threshold     : {min_coherence:.6f}")
    print(f"passed_any    : {passed}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--min-coherence", type=float, default=0.95)
    args = ap.parse_args()
    run(args.input, args.min_coherence)