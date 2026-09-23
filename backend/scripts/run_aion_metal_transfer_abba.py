#!/usr/bin/env python3
"""Compare blocking and fused blocking Metal expert transfers under one load."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import gc
import hashlib
import json
from pathlib import Path
import statistics
import time
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from backend.modules.aion_inference import AdaptiveInferenceRuntime, ExpertRouteCorpus
from backend.scripts.run_aion_layer_scoped_moe_experiment import (
    LayerAheadCoordinator,
    _chat_tokens,
    _layer_scoped_forward,
)
from backend.scripts.run_aion_moe_end_to_end_fault_in import _memory_snapshot, _sha256
from backend.scripts.run_aion_moe_latency_attribution import (
    DEFAULT_PROMPT,
    TimedPackedLayerStore,
    _canonical_sha256,
    _disk_snapshot,
    _verify_storage_device,
    _timed_forward,
    summarize_stage_seconds,
)


CONDITION_ORDER = ("blocking", "fused_blocking", "blocking", "fused_blocking")
STAGE_NAMES = (
    "shared_and_interlayer_sync",
    "router_and_route_capture",
    "expert_dispatch",
    "cache_lookup",
    "storage_and_safetensors_read",
    "cpu_page_materialization",
    "metal_transfer_enqueue",
    "metal_transfer_sync",
    "expert_compute_and_combine",
    "cache_policy_and_eviction",
)


def _p95(values: list[float]) -> float:
    """Conservative nearest-rank p95 for the deliberately small ABBA sample."""
    if not values:
        raise ValueError("p95 requires observations")
    return max(values)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--shard-manifest", type=Path, required=True)
    parser.add_argument("--pack-manifest", type=Path, required=True)
    parser.add_argument(
        "--candidate-pack-manifest",
        type=Path,
        help="Optional execution-representation pack for a source/candidate ABBA comparison.",
    )
    parser.add_argument("--route-corpus", type=Path, required=True)
    parser.add_argument("--memory-budget-gib", type=float, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--generated-tokens", type=int, default=24)
    parser.add_argument(
        "--uninstrumented",
        action="store_true",
        help="Use the production-like layer forward without stage-boundary synchronizations.",
    )
    parser.add_argument(
        "--parallel-materialize-workers",
        type=int,
        help="Compare blocking transfer with exact parallel CPU materialization first.",
    )
    parser.add_argument(
        "--zstd-decode-workers",
        type=int,
        help="Use coalesced reads and this bounded worker count for compressed candidate packs.",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.storage_root.resolve()
    paths = {
        "model": args.model_path.resolve(),
        "shards": args.shard_manifest.resolve(),
        "packs": args.pack_manifest.resolve(),
        "route_corpus": args.route_corpus.resolve(),
    }
    if args.candidate_pack_manifest is not None:
        paths["candidate_packs"] = args.candidate_pack_manifest.resolve()
    output = (args.output or root / "experiments" / f"{args.run_id}.json").resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all artifacts must reside on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    if args.generated_tokens < 1 or args.memory_budget_gib <= 0:
        raise SystemExit("generated tokens and memory budget must be positive")
    if args.parallel_materialize_workers is not None and args.parallel_materialize_workers < 1:
        raise SystemExit("parallel materialization workers must be positive")
    if args.parallel_materialize_workers is not None and args.candidate_pack_manifest is not None:
        raise SystemExit("parallel materialization and candidate-pack comparisons are separate")
    if args.zstd_decode_workers is not None and args.zstd_decode_workers < 2:
        raise SystemExit("zstd decode workers must be at least two")
    if args.zstd_decode_workers is not None and args.candidate_pack_manifest is None:
        raise SystemExit("zstd decode workers require a candidate pack")
    if not torch.backends.mps.is_available():
        raise SystemExit("Apple Metal/MPS is required")
    _verify_storage_device(root, args.device)

    shards = json.loads(paths["shards"].read_text(encoding="utf-8"))
    packs = json.loads(paths["packs"].read_text(encoding="utf-8"))
    candidate_packs = (
        json.loads(paths["candidate_packs"].read_text(encoding="utf-8"))
        if "candidate_packs" in paths else None
    )
    if not all(shards["integrity"].values()) or not all(packs["integrity"].values()):
        raise RuntimeError("manifest integrity gate failed")
    if packs["source_manifest_sha256"] != _sha256(paths["shards"]):
        raise RuntimeError("pack/source manifest binding failed")
    if candidate_packs is not None:
        if not all(candidate_packs["integrity"].values()):
            raise RuntimeError("candidate pack manifest integrity failed")
        if candidate_packs["source_manifest_sha256"] != _sha256(paths["shards"]):
            raise RuntimeError("candidate pack/source manifest binding failed")
        condition_order = ("source_pack", "candidate_pack", "candidate_pack", "source_pack")
    elif args.parallel_materialize_workers is not None:
        condition_order = (
            "blocking", "parallel_materialized", "parallel_materialized", "blocking"
        )
    else:
        condition_order = CONDITION_ORDER

    indexes: list[dict[str, Any]] = []
    entries_by_layer: list[dict[int, dict[str, Any]]] = []
    for number, shard_layer in enumerate(shards["layers"]):
        index_path = Path(shard_layer["index_path"])
        if root not in index_path.resolve().parents:
            raise RuntimeError(f"layer index is outside storage root: {number}")
        if _sha256(index_path) != shard_layer["index_sha256"]:
            raise RuntimeError(f"index integrity failed: layer {number}")
        index = json.loads(index_path.read_text(encoding="utf-8"))
        indexes.append(index)
        entries_by_layer.append({int(entry["expert"]): entry for entry in index["experts"]})
    if len(indexes) != 32 or len(packs["layers"]) != 32:
        raise RuntimeError("expected 32 verified MoE layers")

    corpus = ExpertRouteCorpus(paths["route_corpus"])
    observation_sha256s = tuple(sorted(path.stem for path in corpus.objects.glob("*.json")))
    if not observation_sha256s:
        raise RuntimeError("route corpus contains no observations")
    expected_bindings = {
        "model_config_sha256": _sha256(paths["model"] / "config.json"),
        "shard_manifest_sha256": _sha256(paths["shards"]),
        "pack_manifest_sha256": _sha256(paths["packs"]),
    }
    if corpus.load(observation_sha256s[0])["bindings"] != expected_bindings:
        raise RuntimeError("route corpus does not bind selected artifacts")
    memory_plan = corpus.optimize_memory(
        observation_sha256s,
        entries_by_layer,
        maximum_resident_bytes=int(args.memory_budget_gib * 1024**3),
    )
    capacities = memory_plan.capacities_by_layer

    evidence_root = root / "runtime-evidence" / args.run_id
    runtime = AdaptiveInferenceRuntime(
        replay_path=evidence_root / "replay.sqlite3",
        trace_path=evidence_root / "trace.jsonl",
    )
    routed = runtime.route(args.prompt)
    if not routed.model_call_required or not routed.fallback_prompt:
        raise RuntimeError("ABBA prompt did not reach model fallback")

    load_started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(paths["model"], local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        paths["model"], local_files_only=True, dtype=torch.float16,
        device_map={"": "mps"}, low_cpu_mem_usage=True,
    ).eval()
    checkpoint_load_seconds = time.perf_counter() - load_started
    inputs = _chat_tokens(tokenizer, routed.fallback_prompt)

    def generate() -> dict[str, Any]:
        started = time.perf_counter()
        with torch.inference_mode():
            generated = model.generate(
                **inputs, do_sample=False, max_new_tokens=args.generated_tokens,
                use_cache=True, return_dict_in_generate=True, output_scores=True,
                pad_token_id=tokenizer.eos_token_id,
            )
        torch.mps.synchronize()
        continuation = generated.sequences[0, inputs["input_ids"].shape[1]:].detach().cpu()
        return {
            "token_ids": continuation.tolist(),
            "text": tokenizer.decode(continuation),
            "scores": [score[0].detach().float().cpu() for score in generated.scores],
            "seconds": time.perf_counter() - started,
        }

    control = generate()
    unrestricted_memory = _memory_snapshot("after_unrestricted")
    layers = list(model.model.layers)
    stores: list[TimedPackedLayerStore] = []
    for number, (layer, index, pack_layer) in enumerate(
        zip(layers, indexes, packs["layers"], strict=True)
    ):
        store = TimedPackedLayerStore(number, index, pack_layer)
        store.preverify(root)
        stores.append(store)
        layer.block_sparse_moe.input_linear = None
        layer.block_sparse_moe.output_linear = None
    if candidate_packs is not None:
        if len(candidate_packs["layers"]) != 32:
            raise RuntimeError("expected 32 candidate MoE layer packs")
        for number, (index, pack_layer) in enumerate(
            zip(indexes, candidate_packs["layers"], strict=True)
        ):
            candidate_store = TimedPackedLayerStore(number, index, pack_layer)
            candidate_store.preverify(root)
    gc.collect()
    torch.mps.empty_cache()
    stripped_memory = _memory_snapshot("expert_tensors_removed")

    trials: list[dict[str, Any]] = []
    materialize_executor = (
        ThreadPoolExecutor(
            max_workers=args.parallel_materialize_workers,
            thread_name_prefix="aion-exact-materialize",
        )
        if args.parallel_materialize_workers is not None else None
    )
    zstd_decode_executor = (
        ThreadPoolExecutor(
            max_workers=args.zstd_decode_workers,
            thread_name_prefix="aion-zstd-decode",
        )
        if args.zstd_decode_workers is not None else None
    )
    for store in stores:
        store.materialize_executor = materialize_executor
        store.zstd_decode_executor = zstd_decode_executor
    for sequence, condition in enumerate(condition_order):
        selected_layers = (
            candidate_packs["layers"]
            if condition == "candidate_pack" and candidate_packs is not None
            else packs["layers"]
        )
        for store, selected_pack in zip(stores, selected_layers, strict=True):
            store.clear_all()
            store.pack = selected_pack
            store.transfer_mode = "blocking" if candidate_packs is not None else condition
        gc.collect()
        torch.mps.empty_cache()
        event_starts = [len(store.events) for store in stores]
        stage_seconds = {name: 0.0 for name in STAGE_NAMES}
        coordinator = LayerAheadCoordinator(stores, tuple(() for _ in stores))
        for layer, store, capacity in zip(layers, stores, capacities, strict=True):
            if args.uninstrumented:
                layer.block_sparse_moe.forward = _layer_scoped_forward(
                    layer.block_sparse_moe,
                    store,
                    coordinator,
                    retention_capacity=capacity,
                )
            else:
                layer.block_sparse_moe.forward = _timed_forward(
                    layer.block_sparse_moe, store, coordinator, capacity, stage_seconds
                )
        disk_before = _disk_snapshot(args.device)
        result = generate()
        disk_after = _disk_snapshot(args.device)
        coordinator.close()
        errors = [
            float((observed - expected).abs().max().item())
            for observed, expected in zip(result["scores"], control["scores"], strict=True)
        ]
        activations = [
            event
            for store, start in zip(stores, event_starts, strict=True)
            for event in store.events[start:]
            if event["kind"] == (
                "layer_activation" if args.uninstrumented else "timed_layer_activation"
            )
        ]
        attribution = (
            None if args.uninstrumented
            else summarize_stage_seconds(stage_seconds, result["seconds"])
        )
        trials.append({
            "sequence": sequence,
            "condition": condition,
            "seconds": result["seconds"],
            "tokens_per_second": len(result["token_ids"]) / result["seconds"],
            "token_ids": result["token_ids"],
            "text": result["text"],
            "token_ids_exact_match": result["token_ids"] == control["token_ids"],
            "all_step_logits_exact_match": all(error == 0.0 for error in errors),
            "maximum_step_logit_error": max(errors, default=0.0),
            "demand_faults": sum(event["demand_faults"] for event in activations),
            "demand_logical_bytes": sum(event["demand_logical_bytes"] for event in activations),
            "retained_hits": sum(event["retained_hits"] for event in activations),
            "pack_open_operations": sum(event["demand_faults"] > 0 for event in activations),
            "metal_transfer_operations": sum(
                int(event.get("transfer_operations", 2 * event["demand_faults"]))
                for event in activations
            ),
            "peak_mps_bytes": coordinator.peak_mps_bytes,
            "peak_rss_bytes": coordinator.peak_rss_bytes,
            "attribution": attribution,
            "physical_disk_observation": {
                "device": args.device,
                "read_bytes_delta": disk_after["read_bytes"] - disk_before["read_bytes"],
                "read_count_delta": disk_after["read_count"] - disk_before["read_count"],
                "system_wide_counter": True,
                "exclusive_process_attribution": False,
            },
        })
        for store in stores:
            store.clear_all()

    if materialize_executor is not None:
        materialize_executor.shutdown(wait=True)
    if zstd_decode_executor is not None:
        zstd_decode_executor.shutdown(wait=True)

    control.pop("scores")
    aggregates: dict[str, dict[str, Any]] = {}
    aggregate_conditions = tuple(dict.fromkeys(condition_order))
    for condition in aggregate_conditions:
        group = [trial for trial in trials if trial["condition"] == condition]
        seconds = [float(trial["seconds"]) for trial in group]
        aggregates[condition] = {
            "sample_count": len(group),
            "median_seconds": statistics.median(seconds),
            "p95_seconds_nearest_rank": _p95(seconds),
            "median_tokens_per_second": statistics.median(
                float(trial["tokens_per_second"]) for trial in group
            ),
            "median_metal_transfer_seconds": (
                None if args.uninstrumented else statistics.median(
                    float(trial["attribution"]["stage_seconds"]["metal_transfer_enqueue"])
                    for trial in group
                )
            ),
            "total_demand_logical_bytes": sum(int(trial["demand_logical_bytes"]) for trial in group),
            "maximum_peak_mps_bytes": max(int(trial["peak_mps_bytes"]) for trial in group),
            "maximum_peak_rss_bytes": max(int(trial["peak_rss_bytes"]) for trial in group),
            "all_tokens_exact": all(bool(trial["token_ids_exact_match"]) for trial in group),
            "all_logits_exact": all(bool(trial["all_step_logits_exact_match"]) for trial in group),
            "minimum_attributed_percent": (
                None if args.uninstrumented else min(
                    float(trial["attribution"]["attributed_percent"]) for trial in group
                )
            ),
        }
    reference = aggregates[aggregate_conditions[0]]
    candidate = aggregates[aggregate_conditions[1]]
    median_improvement = 100.0 * (
        1.0 - candidate["median_seconds"] / reference["median_seconds"]
    )
    metal_improvement = (
        None if args.uninstrumented else 100.0 * (
            1.0 - candidate["median_metal_transfer_seconds"] / reference["median_metal_transfer_seconds"]
        )
    )
    gates = {
        "complete_abba_order": tuple(trial["condition"] for trial in trials) == condition_order,
        "all_tokens_exact": all(trial["token_ids_exact_match"] for trial in trials),
        "all_step_logits_exact": all(trial["all_step_logits_exact_match"] for trial in trials),
        "all_runs_at_least_95_percent_attributed": (
            args.uninstrumented or all(
                trial["attribution"]["attributed_percent"] >= 95.0 for trial in trials
            )
        ),
        "expert_resident_memory_within_declared_ceiling": (
            memory_plan.estimated_resident_bytes <= memory_plan.maximum_resident_bytes
        ),
        "candidate_logical_demand_not_higher": (
            candidate["total_demand_logical_bytes"] <= reference["total_demand_logical_bytes"]
        ),
        "candidate_p95_not_higher": candidate["p95_seconds_nearest_rank"] <= reference["p95_seconds_nearest_rank"],
        "median_live_time_improves_at_least_10_percent": median_improvement >= 10.0,
    }
    report = {
        "schema_version": "aion.moe_metal_transfer_abba.v1",
        "run_id": args.run_id,
        "storage_root": str(root),
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": {name: _sha256(path) for name, path in paths.items() if path.is_file()},
        "method": {
            "prompt": args.prompt,
            "prompt_count": 1,
            "generated_tokens_per_trial": args.generated_tokens,
            "condition_order": condition_order,
            "same_model_load": True,
            "empty_expert_cache_before_each_trial": True,
            "cache_condition": "warm_uncontrolled",
            "p95_method": "nearest_rank_max_for_n2",
            "stage_boundary_synchronization": not args.uninstrumented,
            "execution_mode": "uninstrumented" if args.uninstrumented else "stage_instrumented",
            "parallel_materialize_workers": args.parallel_materialize_workers,
            "zstd_decode_workers": args.zstd_decode_workers,
        },
        "capacity_source": {
            "kind": "route_corpus_byte_ceiling",
            "observation_sha256s": observation_sha256s,
            "maximum_resident_bytes": memory_plan.maximum_resident_bytes,
            "estimated_resident_bytes": memory_plan.estimated_resident_bytes,
            "plan_sha256": memory_plan.plan_sha256,
        },
        "gateway": {
            "glyph_address": routed.glyph_address,
            "model_input_sha256": hashlib.sha256(routed.fallback_prompt.encode()).hexdigest(),
            "proof_receipt_sha256": routed.proof_receipt["proof_receipt_sha256"],
        },
        "control": control,
        "trials": trials,
        "aggregates": aggregates,
        "comparison": {
            "reference_condition": aggregate_conditions[0],
            "candidate_condition": aggregate_conditions[1],
            "candidate_median_time_improvement_percent": median_improvement,
            "candidate_median_metal_time_improvement_percent": metal_improvement,
            "promotion_gates": gates,
            "promotion_eligible": all(gates.values()),
        },
        "timing": {"checkpoint_load_seconds": checkpoint_load_seconds},
        "memory": {"unrestricted": unrestricted_memory, "experts_removed": stripped_memory},
        "integrity": {
            "all_32_layer_packs_verified": len(stores) == 32,
            "all_1280_experts_addressable": sum(len(store.verified) for store in stores) == 1280,
            "all_artifacts_on_external_storage": all(root in path.parents for path in (*paths.values(), output)),
            "all_trials_exact": gates["all_tokens_exact"] and gates["all_step_logits_exact"],
            "memory_ceiling_passed": gates["expert_resident_memory_within_declared_ceiling"],
        },
        "claim_boundary": (
            "One prompt with two observations per condition under warm uncontrolled filesystem state. "
            "Stage synchronizations perturb instrumented latency and disk counters are system-wide. Promotion requires "
            "all declared gates; otherwise the result remains diagnostic evidence only."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "report_sha256": report["report_sha256"],
        "aggregates": aggregates,
        "comparison": report["comparison"],
        "integrity": report["integrity"],
    }, indent=2))
    return 0 if all(report["integrity"].values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
