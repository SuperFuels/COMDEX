from __future__ import annotations

import argparse
from symatics_test_common import (
    load_traces_from_jsonl,
    row_label,
    row_phi,
    get_pickup_trace,
    mean_energy,
    trace_drift,
    boundedness_score,
    phase_coherence,
)


def run(path: str, max_drift: float, min_coherence: float, max_boundedness: float) -> None:
    rows = load_traces_from_jsonl(path)

    print("\n=== RESONANCE STABILITY TEST ===\n")

    tested = 0
    passed_any = False

    for idx, r in enumerate(rows):
        trace = get_pickup_trace(r)
        if trace.size < 16:
            continue

        tested += 1

        energy = mean_energy(trace)
        drift = trace_drift(trace)
        bound = boundedness_score(trace)
        coh = phase_coherence(trace)

        stable = (
            drift <= max_drift
            and coh >= min_coherence
            and bound <= max_boundedness
        )

        if stable:
            passed_any = True

        print(
            f"{row_label(r, idx)} | "
            f"phi={row_phi(r):.9f} | "
            f"E={energy:.6f} | "
            f"drift={drift:.6f} | "
            f"bound={bound:.6f} | "
            f"coherence={coh:.6f} | "
            f"stable={stable}"
        )

    print("\n--- SUMMARY ---")
    print(f"tested rows       : {tested}")
    print(f"max_drift         : {max_drift:.6f}")
    print(f"min_coherence     : {min_coherence:.6f}")
    print(f"max_boundedness   : {max_boundedness:.6f}")
    print(f"passed_any        : {passed_any}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--max-drift", type=float, default=0.02)
    ap.add_argument("--min-coherence", type=float, default=0.90)
    ap.add_argument("--max-boundedness", type=float, default=1.25)
    args = ap.parse_args()
    run(args.input, args.max_drift, args.min_coherence, args.max_boundedness)