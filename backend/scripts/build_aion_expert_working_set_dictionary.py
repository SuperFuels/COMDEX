#!/usr/bin/env python3
"""Build and falsify an SD-backed, no-prefetch expert working-set dictionary."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from backend.modules.aion_inference import (
    ExpertRouteCorpus,
    build_expert_working_set_dictionary,
    select_predictive_retention,
    verify_expert_working_set_dictionary,
)
from backend.scripts.run_aion_layer_scoped_moe_experiment import select_frequency_retention
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _simulate(
    batches, entries, capacity: int, *, layer_dictionary: dict[str, Any] | None
) -> tuple[int, int, int]:
    retained: set[int] = set()
    usage_counts: dict[int, int] = {}
    last_used: dict[int, int] = {}
    usage_clock = 0
    demand_bytes = faults = hits = 0
    for batch in batches:
        routes = tuple(tuple(int(expert) for expert in route) for route in batch)
        required = {expert for route in routes for expert in route}
        missing = required - retained
        faults += len(missing)
        hits += len(required & retained)
        demand_bytes += sum(int(entries[expert]["bytes"]) for expert in missing)
        available = retained | required
        if capacity:
            if layer_dictionary is None:
                selected, usage_clock = select_frequency_retention(
                    routes, available, usage_counts, last_used, usage_clock, capacity
                )
            else:
                selected, usage_clock = select_predictive_retention(
                    routes=routes,
                    available_experts=available,
                    usage_counts=usage_counts,
                    last_used=last_used,
                    usage_clock=usage_clock,
                    capacity=capacity,
                    layer_dictionary=layer_dictionary,
                )
            retained = set(selected)
        else:
            retained.clear()
    return demand_bytes, faults, hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--route-corpus", type=Path, required=True)
    parser.add_argument("--shard-manifest", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--memory-budget-gib", type=float, default=3.0)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    root = args.storage_root.resolve()
    corpus_path = args.route_corpus.resolve()
    shard_path = args.shard_manifest.resolve()
    output = (root / "expert-working-sets" / f"{args.run_id}.json").resolve()
    evidence_path = (root / "experiments" / f"{args.run_id}.validation.json").resolve()
    if any(root not in path.parents for path in (corpus_path, shard_path, output, evidence_path)):
        raise SystemExit("all artifacts must remain on external storage")
    if output.exists() or evidence_path.exists():
        raise SystemExit("refusing to overwrite immutable evidence")

    shard_manifest = json.loads(shard_path.read_text(encoding="utf-8"))
    if not all(shard_manifest["integrity"].values()):
        raise RuntimeError("shard manifest integrity gate failed")
    entries_by_layer = []
    for layer in shard_manifest["layers"]:
        index_path = Path(layer["index_path"])
        if _sha256(index_path) != layer["index_sha256"]:
            raise RuntimeError("layer index integrity gate failed")
        index = json.loads(index_path.read_text(encoding="utf-8"))
        entries_by_layer.append({int(item["expert"]): item for item in index["experts"]})

    corpus = ExpertRouteCorpus(corpus_path)
    observation_ids = tuple(sorted(path.stem for path in corpus.objects.glob("*.json")))
    observations = [corpus.load(digest) for digest in observation_ids]
    plan = corpus.optimize_memory(
        observation_ids,
        entries_by_layer,
        maximum_resident_bytes=int(args.memory_budget_gib * 1024**3),
    )
    dictionary = build_expert_working_set_dictionary(observations)
    verify_expert_working_set_dictionary(
        dictionary, expected_bindings=observations[0]["bindings"]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dictionary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    folds = []
    for held_out, observation in zip(observation_ids, observations, strict=True):
        training = [item for item in observations if item["observation_sha256"] != held_out]
        fold_dictionary = build_expert_working_set_dictionary(training)
        baseline = [0, 0, 0]
        candidate = [0, 0, 0]
        for layer, (batches, entries, capacity) in enumerate(zip(
            observation["route_batches_by_layer"],
            entries_by_layer,
            plan.capacities_by_layer,
            strict=True,
        )):
            for totals, result in (
                (baseline, _simulate(batches, entries, capacity, layer_dictionary=None)),
                (candidate, _simulate(
                    batches, entries, capacity,
                    layer_dictionary=fold_dictionary["layers"][layer],
                )),
            ):
                for index, value in enumerate(result):
                    totals[index] += value
        folds.append({
            "held_out_observation_sha256": held_out,
            "baseline_lfu": {"demand_bytes": baseline[0], "faults": baseline[1], "hits": baseline[2]},
            "candidate_predictive_protection": {
                "demand_bytes": candidate[0], "faults": candidate[1], "hits": candidate[2]
            },
            "demand_byte_reduction_percent": 100.0 * (baseline[0] - candidate[0]) / baseline[0],
        })
    baseline_bytes = sum(item["baseline_lfu"]["demand_bytes"] for item in folds)
    candidate_bytes = sum(item["candidate_predictive_protection"]["demand_bytes"] for item in folds)
    baseline_faults = sum(item["baseline_lfu"]["faults"] for item in folds)
    candidate_faults = sum(item["candidate_predictive_protection"]["faults"] for item in folds)
    evidence = {
        "schema_version": "aion.expert_working_set_validation.v1",
        "run_id": args.run_id,
        "paths": {"dictionary": str(output), "route_corpus": str(corpus_path), "shards": str(shard_path)},
        "hashes": {
            "dictionary_sha256": _sha256(output),
            "dictionary_internal_sha256": dictionary["dictionary_sha256"],
            "shard_manifest_sha256": _sha256(shard_path),
            "observation_set_sha256": _canonical_sha256(observation_ids),
        },
        "capacity": {
            "maximum_resident_bytes": plan.maximum_resident_bytes,
            "estimated_resident_bytes": plan.estimated_resident_bytes,
            "capacities_by_layer": plan.capacities_by_layer,
            "plan_sha256": plan.plan_sha256,
        },
        "method": {
            "leave_one_observation_out": True,
            "same_capacity_for_baseline_and_candidate": True,
            "candidate_performs_no_speculative_reads": True,
            "candidate_only_ranks_already_resident_experts": True,
        },
        "folds": folds,
        "aggregate": {
            "baseline_demand_bytes": baseline_bytes,
            "candidate_demand_bytes": candidate_bytes,
            "saved_demand_bytes": baseline_bytes - candidate_bytes,
            "demand_byte_reduction_percent": 100.0 * (baseline_bytes - candidate_bytes) / baseline_bytes,
            "baseline_faults": baseline_faults,
            "candidate_faults": candidate_faults,
            "faults_avoided": baseline_faults - candidate_faults,
            "candidate_won_all_folds": all(item["demand_byte_reduction_percent"] > 0 for item in folds),
        },
        "claim_boundary": (
            "Exact offline replay of three 16-batch route observations under the existing 3 GiB "
            "allocation. It predicts avoided logical demand, not live latency; live SD-backed "
            "token and logit equivalence plus timing remain required before promotion."
        ),
    }
    evidence["report_sha256"] = _canonical_sha256(evidence)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"dictionary": str(output), "evidence": str(evidence_path), **evidence["aggregate"], "report_sha256": evidence["report_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
