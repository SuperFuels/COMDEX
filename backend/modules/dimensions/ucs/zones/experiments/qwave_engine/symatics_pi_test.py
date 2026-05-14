from __future__ import annotations

import argparse
from symatics_test_common import load_traces_from_jsonl, row_label, row_phi


def run(path: str) -> None:
    rows = load_traces_from_jsonl(path)

    print("\n=== PI NOTCH TEST ===\n")

    rows = sorted(rows, key=lambda r: row_phi(r))

    for idx, r in enumerate(rows):
        label = row_label(r, idx)
        phi = row_phi(r)
        pickup = float(r.get("pickup_mean", 0.0))
        print(f"{label} | phi={phi:.9f} | pickup={pickup:.6f}")

    best = min(rows, key=lambda r: float(r.get("pickup_mean", 999999.0)))

    print("\n--- MINIMUM ---")
    print(
        f"{row_label(best)} | "
        f"phi={row_phi(best):.9f} | "
        f"pickup={float(best.get('pickup_mean', 0.0)):.6f}"
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    args = ap.parse_args()
    run(args.input)