from __future__ import annotations

import argparse
from symatics_test_common import load_traces_from_jsonl, get_pickup_trace, exponential_fit


def run(path: str) -> None:
    rows = load_traces_from_jsonl(path)

    print("\n=== E RECOVERY TEST ===\n")

    if not rows:
        print("No rows found.")
        return

    for r in rows:
        trace = get_pickup_trace(r)

        if len(trace) < 50:
            continue

        # take second half only (pseudo recovery)
        segment = trace[len(trace) // 2 :]

        tau, r2 = exponential_fit(segment)

        name = r.get("source_name", r.get("label", "<unknown>"))
        print(f"{name} | tau={tau:.3f} | r2={r2:.4f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    args = ap.parse_args()
    run(args.input)