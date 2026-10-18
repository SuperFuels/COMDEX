#!/usr/bin/env python3
"""Measure a constrained GPT-OSS expert pool on a disjoint exact route trace."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    ordered = sorted(values)
    return ordered[int(fraction * (len(ordered) - 1))]


def analyze(pool: dict, report: dict, start_position: int) -> dict:
    claimed = pool.get("canonical_sha256")
    body = dict(pool)
    body.pop("canonical_sha256", None)
    if (pool.get("schema") != "aion.gptoss-120b-constrained-expert-pool.v1"
            or claimed != canonical_sha256(body)):
        raise ValueError("pool failed schema/hash verification")
    if (report.get("status") != "PASSED"
            or report.get("final_hidden_and_logits_bitwise_repeatable") is not True):
        raise ValueError("holdout report is not passed and repeatable")
    tokens = report["run_a"]["tokens"]
    if not 0 <= start_position < len(tokens):
        raise ValueError("start position is outside the holdout trace")
    pool_layers = {int(layer): set(experts)
                   for layer, experts in pool["layers"].items()}
    if set(pool_layers) != set(range(36)):
        raise ValueError("pool must cover all 36 layers")

    masses: list[float] = []
    missing_counts: list[int] = []
    complete = 0
    per_layer = {layer: {"routes": 0, "complete_routes": 0,
                         "retained_gate_mass": []}
                 for layer in range(36)}
    for token in tokens[start_position:]:
        if len(token["layers"]) != 36:
            raise ValueError("holdout token has incomplete layer coverage")
        for layer_record in token["layers"]:
            layer = int(layer_record["layer"])
            route = layer_record["route"]
            gates = layer_record["gates"]
            if len(route) != 4 or len(gates) != 4:
                raise ValueError("expected four routed experts and gates")
            retained = sum(float(gate) for expert, gate in zip(route, gates)
                           if expert in pool_layers[layer])
            missing = sum(expert not in pool_layers[layer] for expert in route)
            masses.append(retained)
            missing_counts.append(missing)
            per_layer[layer]["routes"] += 1
            per_layer[layer]["complete_routes"] += missing == 0
            per_layer[layer]["retained_gate_mass"].append(retained)
            complete += missing == 0

    route_count = len(masses)
    return {
        "holdout_positions": len(tokens) - start_position,
        "holdout_layer_routes": route_count,
        "complete_layer_routes": complete,
        "complete_layer_route_fraction": complete / route_count,
        "mean_missing_experts_per_route": statistics.fmean(missing_counts),
        "median_retained_gate_mass": statistics.median(masses),
        "p05_retained_gate_mass": percentile(masses, 0.05),
        "p95_retained_gate_mass": percentile(masses, 0.95),
        "routes_with_at_least_0_50_missing_mass": sum(
            mass <= 0.50 for mass in masses) / route_count,
        "per_layer": {
            str(layer): {
                "complete_route_fraction": values["complete_routes"] / values["routes"],
                "median_retained_gate_mass": statistics.median(
                    values["retained_gate_mass"]),
            }
            for layer, values in per_layer.items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--holdout-report", type=Path, required=True)
    parser.add_argument("--start-position", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite holdout evidence")
    pool = json.loads(args.pool.read_text())
    report = json.loads(args.holdout_report.read_text())
    metrics = analyze(pool, report, args.start_position)
    result = {
        "schema": "aion.gptoss-120b-expert-pool-holdout.v1",
        "status": "ANALYZED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "pool_path": str(args.pool.resolve()),
        "pool_file_sha256": hashlib.sha256(args.pool.read_bytes()).hexdigest(),
        "pool_canonical_sha256": pool["canonical_sha256"],
        "holdout_report_path": str(args.holdout_report.resolve()),
        "holdout_report_file_sha256": hashlib.sha256(
            args.holdout_report.read_bytes()).hexdigest(),
        "holdout_start_position": args.start_position,
        "metrics": metrics,
        "claim_boundary": (
            "This is an offline route-coverage gate on a disjoint exact trace. It does not "
            "execute changed-model generation and cannot establish semantic quality or speed."
        ),
    }
    result["canonical_sha256"] = canonical_sha256(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"metrics": metrics, "canonical_sha256": result["canonical_sha256"]},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
