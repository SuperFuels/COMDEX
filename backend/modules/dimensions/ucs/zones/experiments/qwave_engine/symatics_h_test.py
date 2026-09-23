from __future__ import annotations

import argparse
from symatics_test_common import (
    get_pickup_trace,
    load_traces_from_jsonl,
    row_label,
    row_phi,
)


def run(path: str):
    rows = load_traces_from_jsonl(path)

    print("\n=== H PLATEAU TEST ===\n")

    ranked = []

    for r in rows:
        trace = get_pickup_trace(r)

        if len(trace) == 0:
            energy = float(r.get("energy_proxy", 0.0) or 0.0)
        else:
            energy = float((trace * trace).mean())

        ranked.append((row_phi(r), row_label(r), energy))

    ranked.sort(key=lambda x: x[0])

    energies = [e for _, _, e in ranked]

    for phi, label, energy in ranked:
        print(f"{label} | phi={phi:.9f} | energy={energy:.6f}")

    gaps = [abs(energies[i + 1] - energies[i]) for i in range(len(energies) - 1)]

    if gaps:
        print(f"\nmean gap: {sum(gaps) / len(gaps):.6f}")
        print(f"min gap : {min(gaps):.6f}")
        print(f"max gap : {max(gaps):.6f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    args = ap.parse_args()
    run(args.input)