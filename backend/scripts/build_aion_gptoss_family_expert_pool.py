#!/usr/bin/env python3
"""Build a bounded multi-trace GPT-OSS workbench without holdout leakage."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from backend.scripts.run_aion_gptoss_route_cartridge_gate import (
    canonical_sha256,
    expert_sizes,
)


def select_pool(
    scores: dict[tuple[int, int], float],
    sizes: dict[tuple[int, int], int],
    capacity: int,
    minimum_per_layer: int,
) -> tuple[set[tuple[int, int]], int]:
    selected: set[tuple[int, int]] = set()
    resident = 0
    for layer in range(36):
        candidates = [(layer, expert) for expert in range(128)]
        candidates.sort(key=lambda key: (-scores.get(key, 0.0), sizes[key], key))
        for key in candidates[:minimum_per_layer]:
            selected.add(key)
            resident += sizes[key]
    if resident > capacity:
        raise ValueError("minimum per-layer coverage exceeds capacity")
    remaining = [key for key in sizes if key not in selected]
    remaining.sort(key=lambda key: (
        -(scores.get(key, 0.0) / sizes[key]),
        -scores.get(key, 0.0), sizes[key], key,
    ))
    for key in remaining:
        size = sizes[key]
        if scores.get(key, 0.0) > 0.0 and resident + size <= capacity:
            selected.add(key)
            resident += size
    return selected, resident


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--route-report", action="append", type=Path, required=True)
    parser.add_argument("--capacity-gib", type=float, required=True)
    parser.add_argument("--minimum-per-layer", type=int, default=4)
    parser.add_argument("--score", choices=("frequency", "gate-mass"),
                        default="gate-mass")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite expert pool")
    if not 4 <= args.minimum_per_layer <= 128:
        raise SystemExit("minimum-per-layer must be between 4 and 128")
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("status") != "COMPLETE_VERIFIED":
        raise SystemExit("warehouse is not complete and verified")
    _, sizes = expert_sizes(manifest)
    scores: collections.defaultdict[tuple[int, int], float] = collections.defaultdict(float)
    sources = []
    for path in args.route_report:
        report = json.loads(path.read_text())
        if (report.get("status") != "PASSED"
                or report.get("final_hidden_and_logits_bitwise_repeatable") is not True):
            raise SystemExit(f"training report is not passed and repeatable: {path}")
        tokens = report["run_a"]["tokens"]
        for token in tokens:
            if len(token["layers"]) != 36:
                raise SystemExit(f"training report has incomplete layer coverage: {path}")
            for record in token["layers"]:
                layer = int(record["layer"])
                for expert, gate in zip(record["route"], record["gates"]):
                    scores[(layer, int(expert))] += (
                        1.0 if args.score == "frequency" else float(gate))
        sources.append({
            "path": str(path.resolve()),
            "tokens_used": len(tokens),
            "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "canonical_sha256": report.get("canonical_sha256"),
        })
    capacity = int(args.capacity_gib * 1024 ** 3)
    selected, resident = select_pool(scores, sizes, capacity, args.minimum_per_layer)
    layers = {str(layer): sorted(expert for selected_layer, expert in selected
                                 if selected_layer == layer) for layer in range(36)}
    result = {
        "schema": "aion.gptoss-120b-constrained-expert-pool.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "quality_track": True,
        "selection": f"multi-trace {args.score} per raw byte with per-layer floor",
        "capacity_bytes": capacity,
        "resident_raw_bytes": resident,
        "total_layer_experts": len(selected),
        "minimum_experts_per_layer": min(map(len, layers.values())),
        "maximum_experts_per_layer": max(map(len, layers.values())),
        "minimum_per_layer_floor": args.minimum_per_layer,
        "score": args.score,
        "sources": sources,
        "warehouse_manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "layers": layers,
        "claim_boundary": (
            "The pool was learned only from the declared numerical route traces. All weights "
            "remain original, but later router eligibility is constrained. This is a changed-"
            "model quality track and not unrestricted exact GPT-OSS 120B inference."
        ),
    }
    result["canonical_sha256"] = canonical_sha256(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in (
        "resident_raw_bytes", "total_layer_experts", "minimum_experts_per_layer",
        "maximum_experts_per_layer", "canonical_sha256",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
