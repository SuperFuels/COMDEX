#!/usr/bin/env python3
"""Measure the exact expert-load reuse ceiling for layer-major token blocks."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: dict) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()


def percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[int(fraction * (len(values) - 1))]


def analyze(tokens: list[dict], positions: int) -> dict:
    selected = tokens[:positions]
    naive = positions * 36 * 4
    unique_counts = []
    for layer in range(36):
        unique_counts.append(len({expert for token in selected
                                  for expert in token["layers"][layer]["route"]}))
    grouped = sum(unique_counts)
    return {
        "positions": positions,
        "naive_layer_expert_uses": naive,
        "layer_major_unique_expert_loads": grouped,
        "ideal_expert_load_traffic_reduction": naive / grouped,
        "unique_experts_per_layer_p50": statistics.median(unique_counts),
        "unique_experts_per_layer_p95": percentile(unique_counts, .95),
        "unique_experts_per_layer_min": min(unique_counts),
        "unique_experts_per_layer_max": max(unique_counts),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    traces = []
    for path in args.trace:
        report = json.loads(path.read_text())
        tokens = report.get("run_a", {}).get("tokens", [])
        if len(tokens) < 8:
            raise SystemExit("trace must contain at least eight token positions")
        if not report.get("routes_repeatable") or not report.get(
                "final_hidden_and_logits_bitwise_repeatable"):
            raise SystemExit("trace did not pass exact repeatability")
        traces.append({
            "path": str(path.resolve()),
            "file_sha256": digest(path),
            "source_canonical_sha256": report.get("canonical_sha256"),
            "routes_repeatable": True,
            "hidden_and_logits_bitwise_repeatable": True,
            "prefixes": [analyze(tokens, positions) for positions in (2, 4, 8)],
        })
    eight = [trace["prefixes"][-1]["ideal_expert_load_traffic_reduction"]
             for trace in traces]
    passed_narrow = min(eight) > 1.10
    report = {
        "schema": "aion.gptoss-120b-block-verification-bound.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "track": "exact_route_trace_analytical_bound",
        "status": "ADVANCE_EXACT_BLOCK_PROTOTYPE" if passed_narrow else "STOP_BLOCK_REUSE",
        "traces": traces,
        "eight_position_reduction_p50": statistics.median(eight),
        "eight_position_reduction_min": min(eight),
        "eight_position_reduction_max": max(eight),
        "acceptance": {
            "all_source_traces_bitwise_repeatable": True,
            "all_eight_position_bounds_above_1_10x": passed_narrow,
            "measured_runtime_speedup": False,
        },
        "claim_boundary": (
            "Analytical expert-load lower bound from exact observed routes. It assumes one "
            "load per unique layer/expert in a token block and excludes draft cost, rejected "
            "tokens, batched kernel efficiency and implementation overhead. It is not a "
            "measured tokens-per-second result."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"],
                      "eight_position_reduction_p50": report["eight_position_reduction_p50"],
                      "range": [min(eight), max(eight)],
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
