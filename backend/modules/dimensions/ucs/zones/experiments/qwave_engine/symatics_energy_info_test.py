from __future__ import annotations

import argparse
from symatics_test_common import (
    load_traces_from_jsonl,
    row_label,
    row_phi,
    get_pickup_trace,
    mean_energy,
    phase_rate,
    safe_mean,
    safe_std,
)


def run(path: str) -> None:
    rows = load_traces_from_jsonl(path)

    print("\n=== ENERGY / INFORMATION DUALITY TEST ===\n")

    products = []

    for idx, r in enumerate(rows):
        trace = get_pickup_trace(r)
        if trace.size < 16:
            continue

        energy = mean_energy(trace)
        info_rate = phase_rate(trace)
        product = energy * info_rate

        products.append(product)

        print(
            f"{row_label(r, idx)} | "
            f"phi={row_phi(r):.9f} | "
            f"E={energy:.6f} | "
            f"I={info_rate:.6f} | "
            f"E*I={product:.6f}"
        )

    mean_k = safe_mean(products)
    std_k = safe_std(products)
    cv_k = (std_k / mean_k) if mean_k > 1e-12 else 0.0

    print("\n--- SUMMARY ---")
    print(f"tested rows   : {len(products)}")
    print(f"mean(E*I)     : {mean_k:.6f}")
    print(f"std(E*I)      : {std_k:.6f}")
    print(f"cv(E*I)       : {cv_k:.6f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    args = ap.parse_args()
    run(args.input)