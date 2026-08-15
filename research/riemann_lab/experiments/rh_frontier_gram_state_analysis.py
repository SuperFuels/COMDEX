#!/usr/bin/env python3
"""Analyse a persistent Gram-rover state without promoting curve fits to proofs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from flint import arb, ctx


def canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def fit_window(pivots: list[arb], start: int, end: int) -> dict:
    candidates = []
    for quarter_power in range(17):
        power = quarter_power / 4
        values = [
            float(((pivots[n - 1] / pivots[n - 2]) * n**power).mid())
            for n in range(start, end + 1)
        ]
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        spread = math.sqrt(variance) / abs(mean) if mean else math.inf
        candidates.append(
            {"power": power, "mean_C": mean, "relative_spread": spread}
        )
    candidates.sort(key=lambda row: row["relative_spread"])
    return {
        "start": start,
        "end": end,
        "best": candidates[0],
        "top_three": candidates[:3],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("state", type=Path)
    parser.add_argument("--window", type=int, default=30)
    parser.add_argument("--step", type=int, default=25)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    state = json.loads(args.state.read_text(encoding="utf-8"))
    saved_hash = state.get("state_sha256")
    core = {key: value for key, value in state.items() if key != "state_sha256"}
    if canonical_hash(core) != saved_hash:
        raise SystemExit("state hash verification failed")
    ctx.dps = state["digits"]
    pivots = [arb(value) for value in state["pivots"]]
    if not pivots or not all(value > 0 for value in pivots):
        raise SystemExit("state does not contain an all-positive pivot prefix")

    decreasing = [
        bool(pivots[n].upper() < pivots[n - 1].lower())
        for n in range(1, len(pivots))
    ]
    windows = []
    first_start = max(2, args.step)
    for start in range(first_start, len(pivots) - args.window + 2, args.step):
        end = start + args.window - 1
        windows.append(fit_window(pivots, start, end))
    tail_start = max(2, len(pivots) - args.window + 1)
    if not windows or windows[-1]["end"] != len(pivots):
        windows.append(fit_window(pivots, tail_start, len(pivots)))

    best_powers = [window["best"]["power"] for window in windows]
    stable_power = max(best_powers) - min(best_powers) <= 0.25
    payload = {
        "experiment": "gram_rover_pivot_invariant_stability",
        "source_state": str(args.state),
        "source_state_sha256": saved_hash,
        "completed_order": len(pivots),
        "digits": state["digits"],
        "certified_all_pivots_positive": True,
        "certified_strict_decrease_count": sum(decreasing),
        "transition_count": len(decreasing),
        "power_grid": "0, 0.25, ..., 4",
        "windows": windows,
        "best_power_range": [min(best_powers), max(best_powers)],
        "stable_power_at_quarter_grid_resolution": stable_power,
        "decision": (
            "retain_power_law_candidate_for_symbolic_attack"
            if stable_power else
            "reject_current_single_power_fit_as_unstable_across_windows"
        ),
        "claim_boundary": (
            "Positivity and strict-decrease counts are interval-certified. Power-law fits "
            "use midpoints and are diagnostic only; they provide no all-n inequality."
        ),
    }
    payload["payload_sha256"] = canonical_hash(payload)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
