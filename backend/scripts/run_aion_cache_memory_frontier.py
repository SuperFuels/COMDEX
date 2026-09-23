#!/usr/bin/env python3
"""Build an SD-backed, leave-one-out cache frontier under byte ceilings."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from backend.modules.aion_inference import (
    ExpertRouteCorpus,
    optimize_expert_cache_memory_budget,
    simulate_frequency_cache_demand_bytes,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _routes(observations: Sequence[dict[str, Any]], layers: int) -> tuple[tuple, ...]:
    combined: list[list[tuple]] = [[] for _ in range(layers)]
    for observation in observations:
        for layer, batches in enumerate(observation["route_batches_by_layer"]):
            combined[layer].extend(
                tuple(tuple(int(expert) for expert in route) for route in batch)
                for batch in batches
            )
    return tuple(tuple(layer) for layer in combined)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--shard-manifest", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--budget-gib", type=float, nargs="+", default=(1.0, 2.0, 3.0),
        help="Conservative maximum retained-expert bytes for each frontier point.",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.storage_root.resolve()
    corpus_root = args.corpus.resolve()
    manifest_path = args.shard_manifest.resolve()
    output = (args.output or root / "experiments" / f"{args.run_id}.json").resolve()
    if any(root not in path.parents for path in (corpus_root, manifest_path, output)):
        raise SystemExit("corpus, manifest and output must reside on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    budgets = tuple(sorted({int(value * 1024**3) for value in args.budget_gib}))
    if not budgets or any(value <= 0 for value in budgets):
        raise SystemExit("all memory budgets must be positive")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not all(manifest.get("integrity", {}).values()):
        raise RuntimeError("shard manifest integrity gate failed")
    entries_by_layer = []
    for layer in manifest["layers"]:
        index_path = Path(layer["index_path"]).resolve()
        if root not in index_path.parents or _sha256(index_path) != layer["index_sha256"]:
            raise RuntimeError(f"layer {layer['layer']} index integrity failed")
        index = json.loads(index_path.read_text(encoding="utf-8"))
        entries_by_layer.append({int(entry["expert"]): entry for entry in index["experts"]})

    corpus = ExpertRouteCorpus(corpus_root)
    digests = tuple(sorted(path.stem for path in corpus.objects.glob("*.json")))
    if len(digests) < 3:
        raise RuntimeError("leave-one-out frontier requires at least three observations")
    observations = [corpus.load(digest) for digest in digests]
    binding = observations[0]["bindings"]
    architecture = observations[0]["architecture"]
    if any(item["bindings"] != binding for item in observations[1:]):
        raise RuntimeError("corpus mixes model or manifest bindings")
    if any(item["architecture"] != architecture for item in observations[1:]):
        raise RuntimeError("corpus mixes architectures")
    if len(entries_by_layer) != int(architecture["layers"]):
        raise RuntimeError("corpus and manifest layer counts differ")

    folds = []
    for held_out_index, held_out in enumerate(observations):
        training = [item for index, item in enumerate(observations) if index != held_out_index]
        training_routes = _routes(training, len(entries_by_layer))
        held_out_routes = _routes((held_out,), len(entries_by_layer))
        frontier = []
        for budget in budgets:
            plan = optimize_expert_cache_memory_budget(
                training_routes, entries_by_layer, maximum_resident_bytes=budget
            )
            held_out_demand = sum(
                simulate_frequency_cache_demand_bytes(routes, entries, capacity)
                for routes, entries, capacity in zip(
                    held_out_routes, entries_by_layer, plan.capacities_by_layer, strict=True
                )
            )
            uniform_held_out = sum(
                simulate_frequency_cache_demand_bytes(routes, entries, plan.uniform_capacity)
                for routes, entries in zip(held_out_routes, entries_by_layer, strict=True)
            )
            frontier.append({
                "maximum_resident_bytes": budget,
                "estimated_resident_bytes": plan.estimated_resident_bytes,
                "headroom_bytes": budget - plan.estimated_resident_bytes,
                "total_capacity": sum(plan.capacities_by_layer),
                "capacities_by_layer": plan.capacities_by_layer,
                "training_predicted_demand_bytes": plan.predicted_demand_bytes,
                "uniform_capacity": plan.uniform_capacity,
                "held_out_demand_bytes": held_out_demand,
                "uniform_held_out_demand_bytes": uniform_held_out,
                "held_out_reduction_percent": (
                    100.0 * (1.0 - held_out_demand / uniform_held_out)
                    if uniform_held_out else 0.0
                ),
                "plan_sha256": plan.plan_sha256,
            })
        folds.append({
            "held_out_observation_sha256": held_out["observation_sha256"],
            "training_observation_sha256s": [item["observation_sha256"] for item in training],
            "frontier": frontier,
        })

    aggregate = []
    for budget in budgets:
        points = [
            point for fold in folds for point in fold["frontier"]
            if point["maximum_resident_bytes"] == budget
        ]
        learned = sum(point["held_out_demand_bytes"] for point in points)
        uniform = sum(point["uniform_held_out_demand_bytes"] for point in points)
        aggregate.append({
            "maximum_resident_bytes": budget,
            "folds": len(points),
            "learned_held_out_demand_bytes": learned,
            "uniform_held_out_demand_bytes": uniform,
            "held_out_reduction_percent": 100.0 * (1.0 - learned / uniform) if uniform else 0.0,
            "learned_fold_wins": sum(
                point["held_out_demand_bytes"] < point["uniform_held_out_demand_bytes"]
                for point in points
            ),
        })

    integrity = {
        "all_artifacts_on_external_storage": True,
        "shard_manifest_and_layer_indices_verified": True,
        "corpus_objects_content_hash_verified": True,
        "bindings_and_architecture_consistent": True,
        "leave_one_out_folds_complete": len(folds) == len(observations),
        "all_plans_within_declared_memory_ceiling": all(
            point["estimated_resident_bytes"] <= point["maximum_resident_bytes"]
            for fold in folds for point in fold["frontier"]
        ),
    }
    report = {
        "schema_version": "aion.expert_cache_memory_frontier.v1",
        "run_id": args.run_id,
        "storage_root": str(root),
        "corpus_root": str(corpus_root),
        "shard_manifest": str(manifest_path),
        "bindings": binding,
        "hashes": {"shard_manifest_sha256": _sha256(manifest_path)},
        "method": {
            "selection": "exact non-dominated dynamic program under conservative per-layer slot bytes",
            "validation": "leave one route observation out",
            "budgets_bytes": budgets,
            "observations": len(observations),
            "physical_model_execution": False,
        },
        "folds": folds,
        "aggregate": aggregate,
        "integrity": integrity,
        "claim_boundary": (
            "This is exact policy replay over verified SD-backed routes, not a timed model run. "
            "It measures predicted logical demand and budget compliance; latency, peak Metal "
            "allocation and token/logit equivalence require subsequent live execution."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output), "report_sha256": report["report_sha256"],
        "aggregate": aggregate, "integrity": integrity,
    }, indent=2))
    return 0 if all(integrity.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
