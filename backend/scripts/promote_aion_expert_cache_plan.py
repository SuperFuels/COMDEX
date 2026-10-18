#!/usr/bin/env python3
"""Promote a passing adaptive-cache experiment into an immutable runtime plan."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from backend.modules.aion_inference import ExpertRouteCorpus, verify_promoted_expert_cache_plan


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-evidence", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--plan-id", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.storage_root.resolve()
    source_path = args.source_evidence.resolve()
    output = (args.output or root / "cache-plans" / f"{args.plan_id}.json").resolve()
    if root not in source_path.parents or root not in output.parents:
        raise SystemExit("source evidence and promoted plan must reside on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite promoted plan: {output}")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if source.get("schema_version") not in {
        "aion.adaptive_cache_budget_experiment.v1",
        "aion.adaptive_cache_budget_experiment.v2",
    }:
        raise RuntimeError("unsupported adaptive-cache evidence schema")
    claimed_report_hash = source.get("report_sha256")
    report_payload = {key: value for key, value in source.items() if key != "report_sha256"}
    if claimed_report_hash != _canonical_sha256(report_payload):
        raise RuntimeError("source evidence canonical hash failed")
    if not source.get("integrity") or not all(source["integrity"].values()):
        raise RuntimeError("source evidence integrity gate failed")
    model_path = Path(source["paths"]["model"])
    shard_path = Path(source["paths"]["shards"])
    pack_path = Path(source["paths"]["packs"])
    profile_path = Path(source["paths"]["profile"])
    bound_paths = (model_path / "config.json", shard_path, pack_path, profile_path)
    if any(root not in path.resolve().parents for path in bound_paths):
        raise RuntimeError("source bindings escaped external storage")

    corpus_verified = source["schema_version"].endswith(".v1")
    corpus_observation_sha256s: list[str] = []
    if source["schema_version"].endswith(".v2"):
        corpus_evidence = source.get("route_corpus") or {}
        corpus_root = Path(corpus_evidence.get("root", "")).resolve()
        corpus_observation_sha256s = list(corpus_evidence.get("observation_sha256s") or [])
        if root not in corpus_root.parents or not corpus_observation_sha256s:
            raise RuntimeError("v2 evidence is missing an external route corpus")
        corpus = ExpertRouteCorpus(corpus_root)
        observations = [corpus.load(digest) for digest in corpus_observation_sha256s]
        expected_bindings = {
            "model_config_sha256": _sha256(model_path / "config.json"),
            "shard_manifest_sha256": _sha256(shard_path),
            "pack_manifest_sha256": _sha256(pack_path),
        }
        expected_observations = len(source.get("method", {}).get("training_cases", ()))
        corpus_verified = (
            expected_observations > 0
            and len(corpus_observation_sha256s) == expected_observations
            and len(set(corpus_observation_sha256s)) == expected_observations
            and all(
                observation["bindings"] == expected_bindings
                and len(observation["route_batches_by_layer"]) == 32
                and all(observation["route_batches_by_layer"])
                for observation in observations
            )
        )
        if not corpus_verified:
            raise RuntimeError("route corpus binding or completeness gate failed")

    outcomes = source["outcomes"]
    promotion_gates = {
        "source_integrity_passed": all(source["integrity"].values()),
        "all_outputs_exact": source["integrity"]["all_token_ids_and_step_logits_exact"],
        "held_out_median_time_improved": outcomes["adaptive_improves_held_out_median_time"],
        "held_out_demand_bytes_improved": outcomes["adaptive_improves_held_out_demand_bytes"],
        "capacity_preserved": source["integrity"]["global_capacity_exactly_512"],
        "route_corpus_verified": corpus_verified,
    }
    if not all(promotion_gates.values()):
        raise RuntimeError("adaptive cache plan failed promotion gates")

    plan = source["budget_plan"]
    document: dict[str, Any] = {
        "schema_version": "aion.promoted_expert_cache_plan.v1",
        "plan_id": args.plan_id,
        "policy": "bounded_frequency_lfu",
        "architecture": {"layers": 32, "experts_per_layer": 40},
        "total_capacity": int(plan["total_capacity"]),
        "capacities_by_layer": list(plan["capacities_by_layer"]),
        "training_plan_sha256": plan["plan_sha256"],
        "bindings": {
            "model_config_path": str(model_path / "config.json"),
            "model_config_sha256": _sha256(model_path / "config.json"),
            "profile_path": str(profile_path),
            "profile_sha256": _sha256(profile_path),
            "shard_manifest_path": str(shard_path),
            "shard_manifest_sha256": _sha256(shard_path),
            "pack_manifest_path": str(pack_path),
            "pack_manifest_sha256": _sha256(pack_path),
            "source_evidence_path": str(source_path),
            "source_evidence_file_sha256": _sha256(source_path),
            "source_evidence_report_sha256": claimed_report_hash,
            "route_corpus_observation_sha256s": corpus_observation_sha256s,
        },
        "measured_outcomes": {
            "held_out_median_time_change_percent": outcomes["adaptive_time_change_percent_vs_uniform"],
            "held_out_demand_byte_reduction_percent": outcomes[
                "adaptive_demand_byte_reduction_percent_vs_uniform"
            ],
            "held_out_peak_mps_change_percent": outcomes[
                "adaptive_peak_mps_change_percent_vs_uniform"
            ],
        },
        "promotion_gates": promotion_gates,
        "integrity": {
            "capacity_sum_matches": sum(plan["capacities_by_layer"]) == int(plan["total_capacity"]),
            "all_capacities_in_native_range": all(
                0 <= int(value) <= 40 for value in plan["capacities_by_layer"]
            ),
            "all_32_layers_present": len(plan["capacities_by_layer"]) == 32,
            "source_evidence_hash_verified": True,
            "model_and_manifests_bound": True,
            "promotion_gates_passed": all(promotion_gates.values()),
        },
        "claim_boundary": (
            "This plan is promoted for reproducible experimental use on the bound Granite model "
            "and manifests. It is not a universal capacity allocation or production SLA."
        ),
    }
    if not all(document["integrity"].values()):
        raise RuntimeError("promoted document integrity gate failed")
    document["artifact_sha256"] = _canonical_sha256(document)
    verify_promoted_expert_cache_plan(
        document,
        expected_model_config_sha256=document["bindings"]["model_config_sha256"],
        expected_shard_manifest_sha256=document["bindings"]["shard_manifest_sha256"],
        expected_pack_manifest_sha256=document["bindings"]["pack_manifest_sha256"],
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "file_sha256": _sha256(output),
        "artifact_sha256": document["artifact_sha256"],
        "total_capacity": document["total_capacity"],
        "promotion_gates": promotion_gates,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
