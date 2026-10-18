#!/usr/bin/env python3
"""Falsifiable, byte-budgeted route-cartridge analysis for GPT-OSS 120B."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RouteKey = tuple[int, int]


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()


def expert_sizes(manifest: dict[str, Any]) -> tuple[dict[RouteKey, int], dict[RouteKey, int]]:
    compressed: dict[RouteKey, int] = collections.defaultdict(int)
    raw: dict[RouteKey, int] = collections.defaultdict(int)
    for region in manifest["regions"]:
        name = region["region_name"]
        if not (name.startswith("blk.") and ".ffn_" in name and "_exps." in name):
            continue
        layer = int(name.split(".")[1])
        for frame in region["frames"]:
            key = (layer, int(frame["expert"]))
            compressed[key] += int(frame["compressed_bytes"])
            raw[key] += int(frame["raw_bytes"])
    if len(raw) != 36 * 128 or set(raw) != set(compressed):
        raise ValueError("warehouse does not contain complete 36x128 expert coverage")
    return dict(compressed), dict(raw)


def extract_routes(report: dict[str, Any]) -> list[list[list[int]]]:
    if (report.get("status") != "PASSED"
            or report.get("final_hidden_and_logits_bitwise_repeatable") is not True):
        raise ValueError("route evidence is not passed and bitwise repeatable")
    tokens = report["run_a"]["tokens"]
    result = [[list(layer["route"]) for layer in token["layers"]] for token in tokens]
    if any(len(token) != 36 or any(len(route) != 4 for route in token) for token in result):
        raise ValueError("route evidence is not complete 36-layer top-four routing")
    return result


def compile_cartridge(
    training_tokens: list[list[list[int]]], raw_sizes: dict[RouteKey, int],
    capacity_bytes: int,
) -> set[RouteKey]:
    counts: collections.Counter[RouteKey] = collections.Counter()
    for token in training_tokens:
        for layer, route in enumerate(token):
            counts.update((layer, expert) for expert in route)
    # Greedy value density is deterministic. Ties prefer more observations, smaller
    # weights, then stable layer/expert order.
    ranked = sorted(counts, key=lambda key: (
        -(counts[key] / raw_sizes[key]), -counts[key], raw_sizes[key], key,
    ))
    selected: set[RouteKey] = set()
    resident = 0
    for key in ranked:
        size = raw_sizes[key]
        if resident + size <= capacity_bytes:
            selected.add(key)
            resident += size
    return selected


def evaluate(
    tokens: list[list[list[int]]], selected: set[RouteKey],
    compressed_sizes: dict[RouteKey, int], raw_sizes: dict[RouteKey, int],
) -> dict[str, Any]:
    accesses = hits = total_compressed = missed_compressed = 0
    unique_misses: set[RouteKey] = set()
    for token in tokens:
        for layer, route in enumerate(token):
            for expert in route:
                key = (layer, expert)
                accesses += 1
                total_compressed += compressed_sizes[key]
                if key in selected:
                    hits += 1
                else:
                    unique_misses.add(key)
                    missed_compressed += compressed_sizes[key]
    resident_raw = sum(raw_sizes[key] for key in selected)
    return {
        "accesses": accesses,
        "hits": hits,
        "faults": accesses - hits,
        "route_coverage": hits / accesses if accesses else 0.0,
        "fault_reduction_factor": accesses / (accesses - hits) if accesses != hits else None,
        "resident_experts": len(selected),
        "resident_raw_bytes": resident_raw,
        "total_unretained_compressed_bytes": total_compressed,
        "missed_compressed_bytes": missed_compressed,
        "compressed_byte_reduction": 1.0 - missed_compressed / total_compressed
        if total_compressed else 0.0,
        "unique_missed_experts": len(unique_misses),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--route-family", action="append", required=True,
                        help="NAME=exact-route-report.json; repeat for each family")
    parser.add_argument("--capacity-gib", action="append", type=float,
                        default=[6.0, 8.0, 10.0])
    parser.add_argument("--minimum-coverage", type=float, default=0.90)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("status") != "COMPLETE_VERIFIED":
        raise SystemExit("warehouse is not complete and verified")
    compressed_sizes, raw_sizes = expert_sizes(manifest)
    families: dict[str, tuple[Path, dict[str, Any], list[list[list[int]]]]] = {}
    for item in args.route_family:
        name, separator, path_text = item.partition("=")
        if not separator or not name or name in families:
            raise SystemExit(f"invalid or duplicate route family: {item}")
        path = Path(path_text).resolve()
        report = json.loads(path.read_text())
        families[name] = (path, report, extract_routes(report))

    capacities = sorted(set(int(value * 1024 ** 3) for value in args.capacity_gib))
    results = []
    for capacity in capacities:
        within_family = []
        for name, (_, _, tokens) in families.items():
            split = max(1, len(tokens) // 2)
            selected = compile_cartridge(tokens[:split], raw_sizes, capacity)
            within_family.append({
                "family": name, "training_tokens": split,
                "held_out_tokens": len(tokens) - split,
                **evaluate(tokens[split:], selected, compressed_sizes, raw_sizes),
            })
        leave_one_out = []
        for name, (_, _, tokens) in families.items():
            training = [token for other, (_, _, other_tokens) in families.items()
                        if other != name for token in other_tokens]
            selected = compile_cartridge(training, raw_sizes, capacity)
            leave_one_out.append({"held_out_family": name, "training_tokens": len(training),
                                  "held_out_tokens": len(tokens),
                                  **evaluate(tokens, selected, compressed_sizes, raw_sizes)})
        results.append({
            "capacity_bytes": capacity,
            "capacity_gib": capacity / 1024 ** 3,
            "within_family_prefix_holdout": within_family,
            "leave_one_family_out": leave_one_out,
            "minimum_within_family_coverage": min(x["route_coverage"] for x in within_family),
            "median_within_family_coverage": sorted(x["route_coverage"] for x in within_family)[len(within_family) // 2],
            "minimum_leave_one_family_out_coverage": min(x["route_coverage"] for x in leave_one_out),
        })
    best_minimum = max(item["minimum_within_family_coverage"] for item in results)
    accepted = best_minimum >= args.minimum_coverage
    report = {
        "schema": "aion.gptoss-120b-route-cartridge-gate.v1",
        "status": "ADVANCE_EXACT_ROUTE_CARTRIDGE" if accepted else "STOP_EXACT_ROUTE_CARTRIDGE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "warehouse_manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "route_sources": [{"family": name, "path": str(path),
                           "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                           "canonical_sha256": source.get("canonical_sha256")}
                          for name, (path, source, _) in families.items()],
        "acceptance": {
            "minimum_held_out_route_coverage": args.minimum_coverage,
            "equivalent_maximum_fault_fraction": 1.0 - args.minimum_coverage,
            "best_observed_minimum_within_family_coverage": best_minimum,
            "passed": accepted,
        },
        "capacities": results,
        "decision_rule": (
            "Advance exact cartridge integration only when every prompt family reaches the "
            "predeclared held-out route coverage. A failed gate requires a separately labelled "
            "quality-gated constrained-expert model; it does not authorize changing this threshold."
        ),
        "claim_boundary": (
            "This is an exact simulation over captured, bitwise-repeatable GPT-OSS 120B routes "
            "and verified warehouse byte sizes. It predicts cache faults and bytes; it is not an "
            "executed latency, quality or tokens-per-second result."
        ),
    }
    report["canonical_sha256"] = canonical_sha256(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], **report["acceptance"],
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
