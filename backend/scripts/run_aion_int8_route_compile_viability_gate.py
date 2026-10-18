#!/usr/bin/env python3
"""Measure whether fixed-route compiled INT8 graphs can cover real Granite routes."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import statistics
from typing import Any

from backend.scripts.run_aion_int8_glyph_full_model import _canonical_sha256
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256


def _route_leaves(value: Any) -> list[tuple[int, ...]]:
    leaves: list[tuple[int, ...]] = []
    if (isinstance(value, list) and value and
            all(isinstance(item, (int, float)) for item in value)):
        leaves.append(tuple(sorted(set(int(item) for item in value))))
    elif isinstance(value, list):
        for item in value:
            leaves.extend(_route_leaves(item))
    return leaves


def _coverage(routes: list[tuple[int, ...]], graph_count: int) -> float:
    counts = Counter(routes)
    return sum(count for _, count in counts.most_common(graph_count)) / len(routes)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--route-observation", type=Path, action="append", required=True)
    parser.add_argument("--compiled-graphs-per-layer", type=int, default=8)
    parser.add_argument("--minimum-median-coverage", type=float, default=0.50)
    parser.add_argument("--minimum-repeat-fraction", type=float, default=0.50)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    observations = [path.resolve() for path in args.route_observation]
    output = args.output.resolve()
    if any(root not in path.parents for path in (*observations, output)):
        raise SystemExit("route evidence and output must remain on external storage")
    if output.exists() or args.compiled_graphs_per_layer < 1:
        raise SystemExit("refusing overwrite or invalid graph count")

    layers: list[list[tuple[int, ...]]] = [[] for _ in range(32)]
    for path in observations:
        document = json.loads(path.read_text())
        routed = document.get("route_batches_by_layer")
        if not isinstance(routed, list) or len(routed) != 32:
            raise RuntimeError(f"invalid 32-layer route observation: {path}")
        for index, value in enumerate(routed):
            layers[index].extend(_route_leaves(value))
    if any(not routes for routes in layers):
        raise RuntimeError("every layer must contain route observations")

    layer_reports = []
    for index, routes in enumerate(layers):
        counts = Counter(routes)
        repeated = sum(count - 1 for count in counts.values())
        layer_reports.append({
            "layer": index,
            "observations": len(routes),
            "unique_route_sets": len(counts),
            "exact_repeat_fraction": repeated / len(routes),
            "top_1_coverage": _coverage(routes, 1),
            "top_8_coverage": _coverage(routes, 8),
            "budgeted_graph_coverage": _coverage(routes, args.compiled_graphs_per_layer),
        })
    median_coverage = statistics.median(
        item["budgeted_graph_coverage"] for item in layer_reports)
    total_observations = sum(item["observations"] for item in layer_reports)
    total_unique = sum(item["unique_route_sets"] for item in layer_reports)
    total_repeat_fraction = 1 - total_unique / total_observations
    acceptance = {
        "median_budgeted_graph_coverage_at_least_threshold":
            median_coverage >= args.minimum_median_coverage,
        "aggregate_exact_repeat_fraction_at_least_threshold":
            total_repeat_fraction >= args.minimum_repeat_fraction,
        "all_layers_observed": len(layer_reports) == 32,
    }
    report = {
        "schema_version": "aion.int8_route_compile_viability_gate.v1",
        "paths": [str(path) for path in observations],
        "hashes": [_sha256(path) for path in observations],
        "compiled_graphs_per_layer": args.compiled_graphs_per_layer,
        "minimum_median_coverage": args.minimum_median_coverage,
        "minimum_repeat_fraction": args.minimum_repeat_fraction,
        "layers": layer_reports,
        "aggregate": {
            "observations": total_observations,
            "unique_route_sets_summed_by_layer": total_unique,
            "exact_repeat_fraction": total_repeat_fraction,
            "median_budgeted_graph_coverage": median_coverage,
            "median_top_1_coverage": statistics.median(
                item["top_1_coverage"] for item in layer_reports),
            "median_top_8_coverage": statistics.median(
                item["top_8_coverage"] for item in layer_reports),
        },
        "acceptance": acceptance,
        "decision": ("ADVANCE_ROUTE_SPECIALIZED_COMPILE" if all(acceptance.values())
                     else "STOP_ROUTE_SPECIALIZED_COMPILE"),
        "claim_boundary": ("Observed exact eight-expert route-set reuse only. This gate does not "
                           "measure a future dynamic routed Metal kernel or semantic quality."),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "decision": report["decision"],
                      "aggregate": report["aggregate"], "acceptance": acceptance,
                      "report_sha256": report["report_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
