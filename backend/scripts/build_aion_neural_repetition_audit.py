#!/usr/bin/env python3
"""Audit real MoE routes for reusable weights versus reusable calculations."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
from typing import Any

from backend.modules.aion_inference import ExpertRouteCorpus


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--route-corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, corpus_path, output = (
        args.storage_root.resolve(), args.route_corpus.resolve(), args.output.resolve()
    )
    if any(root not in path.parents for path in (corpus_path, output)):
        raise SystemExit("corpus and evidence must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")

    corpus = ExpertRouteCorpus(corpus_path)
    object_ids = tuple(sorted(path.stem for path in corpus.objects.glob("*.json")))
    observations = [corpus.load(object_id) for object_id in object_ids]
    if not observations or len({
        json.dumps(item["bindings"], sort_keys=True) for item in observations
    }) != 1:
        raise RuntimeError("route observations are empty or bind different artifacts")

    layers = []
    total_routes = total_unique = total_consecutive = total_exact_consecutive = 0
    all_shared = []
    for layer in range(32):
        streams = []
        for observation in observations:
            stream = [
                tuple(int(expert) for expert in route)
                for batch in observation["route_batches_by_layer"][layer]
                for route in batch
            ]
            streams.append(stream)
        flattened = [route for stream in streams for route in stream]
        counts = Counter(flattened)
        pairs = [
            (left, right)
            for stream in streams for left, right in zip(stream, stream[1:])
        ]
        shared = [len(set(left).intersection(right)) for left, right in pairs]
        exact = sum(left == right for left, right in pairs)
        total_routes += len(flattened)
        total_unique += len(counts)
        total_consecutive += len(pairs)
        total_exact_consecutive += exact
        all_shared.extend(shared)
        layers.append({
            "layer": layer, "route_instances": len(flattened),
            "unique_route_sets": len(counts),
            "duplicate_route_instances": len(flattened) - len(counts),
            "duplicate_route_rate_percent": 100 * (
                len(flattened) - len(counts)
            ) / len(flattened),
            "consecutive_route_pairs": len(pairs),
            "exact_consecutive_route_repeats": exact,
            "mean_experts_shared_with_next_route": statistics.mean(shared),
            "median_experts_shared_with_next_route": statistics.median(shared),
            "most_common_route_count": counts.most_common(1)[0][1],
        })

    report = {
        "schema_version": "aion.neural_repetition_audit.v1",
        "route_corpus": str(corpus_path),
        "observation_sha256s": list(object_ids),
        "bindings": observations[0]["bindings"],
        "aggregate": {
            "route_instances": total_routes,
            "unique_route_sets_within_layers": total_unique,
            "duplicate_route_instances": total_routes - total_unique,
            "duplicate_route_rate_percent": 100 * (
                total_routes - total_unique
            ) / total_routes,
            "consecutive_route_pairs": total_consecutive,
            "exact_consecutive_route_repeats": total_exact_consecutive,
            "exact_consecutive_route_repeat_percent": 100 * (
                total_exact_consecutive / total_consecutive
            ),
            "mean_experts_shared_with_next_route": statistics.mean(all_shared),
            "median_experts_shared_with_next_route": statistics.median(all_shared),
            "proven_reusable_expert_outputs": 0,
        },
        "layers": layers,
        "reuse_boundary": {
            "weight_reuse_supported": True,
            "route_repetition_supported": True,
            "output_memoization_supported": False,
            "reason": (
                "The privacy-preserving corpus stores expert identities but not activation "
                "vectors. Identical routes do not imply identical expert inputs. Exact output "
                "reuse requires matching activation, weight and numerical-contract hashes."
            ),
            "required_next_instrumentation": (
                "Record keyed hashes of live per-layer activation vectors without storing "
                "their values, then count exact repeats on a multi-request prefix workload."
            ),
        },
        "claim_boundary": (
            "Offline audit of three content-addressed route observations. It establishes "
            "routing and expert-weight repetition, not reusable neural outputs or speedup."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "output": str(output), "aggregate": report["aggregate"],
        "reuse_boundary": report["reuse_boundary"],
        "report_sha256": report["report_sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
