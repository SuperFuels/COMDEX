#!/usr/bin/env python3
"""Test narrow, confidence-gated, one-layer-ahead SD expert prefetch."""

from __future__ import annotations

import argparse
from concurrent.futures import Future, ThreadPoolExecutor
import gc
import hashlib
import json
import math
from pathlib import Path
import statistics
import time
from typing import Any

import psutil
import torch
import torch.nn.functional as functional
from transformers import AutoModelForCausalLM, AutoTokenizer

from backend.modules.aion_inference import (
    AdaptiveInferenceRuntime,
    ExpertRouteCorpus,
    build_cross_layer_route_capsule,
    predict_cross_layer_experts,
    verify_cross_layer_route_capsule,
)
from backend.scripts.run_aion_layer_pack_experiment import PackedLayerScopedStore
from backend.scripts.run_aion_layer_scoped_moe_experiment import _chat_tokens
from backend.scripts.run_aion_moe_end_to_end_fault_in import _memory_snapshot, _sha256
from backend.scripts.run_aion_moe_latency_attribution import (
    _canonical_sha256,
    _disk_snapshot,
    _verify_storage_device,
)
from backend.scripts.run_aion_promoted_cache_plan_replication import LONGER_CASES


CONDITIONS = ("demand_only", "transition_prefetch")


def _p95(values: list[float]) -> float:
    if not values:
        raise ValueError("p95 requires observations")
    return sorted(values)[math.ceil(0.95 * len(values)) - 1]


class TransitionPrefetchCoordinator:
    """Bound one-layer-ahead CPU reads and reconcile every useful/wasted byte."""

    def __init__(
        self,
        stores: list[PackedLayerScopedStore],
        capsule: dict[str, Any],
        *,
        enabled: bool,
        maximum_cpu_prefetch_bytes: int,
    ) -> None:
        self.stores = stores
        self.capsule = capsule
        verify_cross_layer_route_capsule(capsule)
        self.enabled = enabled
        self.maximum_cpu_prefetch_bytes = maximum_cpu_prefetch_bytes
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="aion-transition")
        self.futures: dict[int, tuple[Future, dict[str, Any]]] = {}
        self.acquired: dict[int, dict[str, Any]] = {}
        self.events: list[dict[str, Any]] = []
        self.wait_seconds: list[float] = []
        self.peak_mps_bytes = 0
        self.peak_rss_bytes = 0

    def acquire(self, layer: int) -> None:
        pending = self.futures.pop(layer, None)
        if pending is None:
            return
        future, event = pending
        started = time.perf_counter()
        worker_event = future.result()
        waited = time.perf_counter() - started
        self.wait_seconds.append(waited)
        event["worker_seconds"] = float(worker_event["seconds"])
        event["acquire_wait_seconds"] = waited
        self.acquired[layer] = event

    def classify(self, layer: int, required: tuple[int, ...]) -> None:
        event = self.acquired.pop(layer, None)
        if event is None:
            return
        required_set = set(required)
        useful = tuple(expert for expert in event["expert_ids"] if expert in required_set)
        wasted = tuple(expert for expert in event["expert_ids"] if expert not in required_set)
        event["useful_expert_ids"] = useful
        event["wasted_expert_ids"] = wasted
        event["useful_bytes"] = sum(
            int(self.stores[layer].entries[expert]["bytes"]) for expert in useful
        )
        event["wasted_bytes"] = sum(
            int(self.stores[layer].entries[expert]["bytes"]) for expert in wasted
        )
        self.events.append(event)

    def schedule(self, source_layer: int, observed_routes: tuple[tuple[int, ...], ...]) -> None:
        if not self.enabled or len(observed_routes) != 1:
            return
        target_layer = source_layer + 1
        if target_layer >= len(self.stores) or target_layer in self.futures:
            return
        target_store = self.stores[target_layer]
        predicted = predict_cross_layer_experts(
            self.capsule,
            target_layer=target_layer,
            source_route=observed_routes[0],
            resident_experts=target_store.retained,
            verify=False,
        )
        if not predicted:
            return
        expert_ids = tuple(int(item["expert"]) for item in predicted)
        logical_bytes = sum(int(target_store.entries[expert]["bytes"]) for expert in expert_ids)
        if logical_bytes > self.maximum_cpu_prefetch_bytes:
            self.events.append({
                "kind": "transition_prefetch_suppressed",
                "source_layer": source_layer,
                "target_layer": target_layer,
                "reason": "cpu_headroom",
                "logical_bytes": logical_bytes,
            })
            return
        event = {
            "kind": "transition_prefetch",
            "source_layer": source_layer,
            "target_layer": target_layer,
            "expert_ids": expert_ids,
            "predictions": predicted,
            "logical_bytes": logical_bytes,
        }
        self.futures[target_layer] = (
            self.executor.submit(target_store.prefetch_to_cpu, expert_ids),
            event,
        )

    def observe_memory(self) -> None:
        self.peak_mps_bytes = max(self.peak_mps_bytes, torch.mps.current_allocated_memory())
        self.peak_rss_bytes = max(self.peak_rss_bytes, psutil.Process().memory_info().rss)

    def close(self) -> None:
        self.executor.shutdown(wait=True)
        if self.futures or self.acquired:
            raise RuntimeError("unreconciled transition prefetch remained at trial end")


def _predictive_forward(
    block,
    store: PackedLayerScopedStore,
    coordinator: TransitionPrefetchCoordinator,
    capacity: int,
):
    router = block.router
    activation = block.activation
    input_size = block.input_size

    def forward(layer_input):
        coordinator.acquire(store.layer)
        batch_size, length, embedding_size = layer_input.size()
        flattened = layer_input.reshape(-1, embedding_size)
        _, batch_index, batch_gates, expert_size, router_logits = router(flattened)
        observed_routes = tuple(
            tuple(sorted(row.topk(router.top_k, dim=-1).indices.tolist()))
            for row in router_logits
        )
        store.route_batches.append(observed_routes)
        expert_inputs = flattened[batch_index]
        input_list = expert_inputs.split(expert_size, dim=0)
        required = tuple(expert for expert, value in enumerate(input_list) if value.shape[0])
        coordinator.classify(store.layer, required)
        coordinator.schedule(store.layer, observed_routes)
        weights = store.activate(required, layer_input.device, layer_input.dtype)
        coordinator.observe_memory()
        output_list = []
        for expert, expert_input in enumerate(input_list):
            if expert_input.shape[0] == 0:
                output_list.append(torch.empty(
                    (0, input_size), dtype=layer_input.dtype, device=layer_input.device
                ))
                continue
            input_weight, output_weight = weights[expert]
            hidden = functional.linear(expert_input, input_weight)
            gate_half, value_half = hidden.chunk(2, dim=-1)
            output_list.append(functional.linear(activation(gate_half) * value_half, output_weight))
        expert_outputs = torch.cat(output_list, dim=0) * batch_gates[:, None]
        zeros = torch.zeros(
            (batch_size * length, input_size),
            dtype=expert_outputs.dtype,
            device=expert_outputs.device,
        )
        result = zeros.index_add(0, batch_index, expert_outputs).view(
            batch_size, length, input_size
        )
        store.release_with_frequency_capacity(observed_routes, capacity)
        return result

    return forward


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--shard-manifest", type=Path, required=True)
    parser.add_argument("--pack-manifest", type=Path, required=True)
    parser.add_argument("--route-corpus", type=Path, required=True)
    parser.add_argument("--memory-budget-gib", type=float, default=3.0)
    parser.add_argument("--confidence-threshold", type=float, default=0.80)
    parser.add_argument("--max-predictions-per-layer", type=int, default=1)
    parser.add_argument("--maximum-cpu-prefetch-mib", type=float, default=8.0)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--generated-tokens", type=int, default=24)
    parser.add_argument("--case-index", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.storage_root.resolve()
    paths = {
        "model": args.model_path.resolve(),
        "shards": args.shard_manifest.resolve(),
        "packs": args.pack_manifest.resolve(),
        "route_corpus": args.route_corpus.resolve(),
    }
    output = (args.output or root / "experiments" / f"{args.run_id}.json").resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all artifacts must reside on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    if args.generated_tokens < 1 or args.memory_budget_gib <= 0:
        raise SystemExit("token and memory budgets must be positive")
    if not torch.backends.mps.is_available():
        raise SystemExit("Apple Metal/MPS is required")
    _verify_storage_device(root, args.device)

    shards = json.loads(paths["shards"].read_text(encoding="utf-8"))
    packs = json.loads(paths["packs"].read_text(encoding="utf-8"))
    if not all(shards["integrity"].values()) or not all(packs["integrity"].values()):
        raise RuntimeError("manifest integrity gate failed")
    if packs["source_manifest_sha256"] != _sha256(paths["shards"]):
        raise RuntimeError("pack/source manifest binding failed")
    indexes = []
    entries_by_layer = []
    for number, shard_layer in enumerate(shards["layers"]):
        index_path = Path(shard_layer["index_path"])
        if root not in index_path.resolve().parents or _sha256(index_path) != shard_layer["index_sha256"]:
            raise RuntimeError(f"index integrity failed: layer {number}")
        index = json.loads(index_path.read_text(encoding="utf-8"))
        indexes.append(index)
        entries_by_layer.append({int(entry["expert"]): entry for entry in index["experts"]})

    corpus = ExpertRouteCorpus(paths["route_corpus"])
    observation_sha256s = tuple(sorted(path.stem for path in corpus.objects.glob("*.json")))
    observations = [corpus.load(digest) for digest in observation_sha256s]
    expected_bindings = {
        "model_config_sha256": _sha256(paths["model"] / "config.json"),
        "shard_manifest_sha256": _sha256(paths["shards"]),
        "pack_manifest_sha256": _sha256(paths["packs"]),
    }
    if not observations or any(item["bindings"] != expected_bindings for item in observations):
        raise RuntimeError("route corpus binding failed")
    memory_plan = corpus.optimize_memory(
        observation_sha256s,
        entries_by_layer,
        maximum_resident_bytes=int(args.memory_budget_gib * 1024**3),
    )
    capacities = memory_plan.capacities_by_layer
    capsule = build_cross_layer_route_capsule(
        observations,
        confidence_threshold=args.confidence_threshold,
        max_predictions_per_layer=args.max_predictions_per_layer,
    )
    verify_cross_layer_route_capsule(capsule, expected_bindings=expected_bindings)
    capsule_path = root / "route-capsules" / f"{capsule['capsule_sha256']}.json"
    capsule_encoded = json.dumps(capsule, indent=2, sort_keys=True) + "\n"
    capsule_path.parent.mkdir(parents=True, exist_ok=True)
    if capsule_path.exists():
        if capsule_path.read_text(encoding="utf-8") != capsule_encoded:
            raise RuntimeError("route capsule content-address collision")
    else:
        with capsule_path.open("x", encoding="utf-8") as handle:
            handle.write(capsule_encoded)

    selected_cases = tuple(LONGER_CASES)
    if args.case_index is not None:
        if args.case_index < 0 or args.case_index >= len(selected_cases):
            raise SystemExit("case-index is outside the prompt corpus")
        selected_cases = (selected_cases[args.case_index],)
    evidence_root = root / "runtime-evidence" / args.run_id
    runtime = AdaptiveInferenceRuntime(
        replay_path=evidence_root / "replay.sqlite3",
        trace_path=evidence_root / "trace.jsonl",
    )
    requests = []
    for number, case in enumerate(selected_cases):
        routed = runtime.route(case["prompt"])
        if not routed.model_call_required or not routed.fallback_prompt:
            raise RuntimeError("transition-prefetch case did not reach model fallback")
        requests.append({
            "case": number if args.case_index is None else args.case_index,
            "public_prompt": case["prompt"],
            "model_input": routed.fallback_prompt,
            "model_input_sha256": hashlib.sha256(routed.fallback_prompt.encode()).hexdigest(),
            "glyph_address": routed.glyph_address,
            "proof_receipt_sha256": routed.proof_receipt["proof_receipt_sha256"],
        })

    load_started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(paths["model"], local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        paths["model"], local_files_only=True, dtype=torch.float16,
        device_map={"": "mps"}, low_cpu_mem_usage=True,
    ).eval()
    checkpoint_load_seconds = time.perf_counter() - load_started

    def generate(model_input: str) -> dict[str, Any]:
        inputs = _chat_tokens(tokenizer, model_input)
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

    controls = [generate(request["model_input"]) for request in requests]
    unrestricted_memory = _memory_snapshot("after_unrestricted")
    layers = list(model.model.layers)
    stores = []
    for number, (layer, index, pack_layer) in enumerate(
        zip(layers, indexes, packs["layers"], strict=True)
    ):
        store = PackedLayerScopedStore(number, index, pack_layer)
        store.preverify(root)
        stores.append(store)
        layer.block_sparse_moe.input_linear = None
        layer.block_sparse_moe.output_linear = None
    gc.collect()
    torch.mps.empty_cache()
    stripped_memory = _memory_snapshot("expert_tensors_removed")

    maximum_cpu_prefetch_bytes = int(args.maximum_cpu_prefetch_mib * 1024**2)
    trials = []
    for request_number, (request, control) in enumerate(zip(requests, controls, strict=True)):
        order = CONDITIONS if request["case"] % 2 == 0 else tuple(reversed(CONDITIONS))
        for sequence, condition in enumerate(order):
            for store in stores:
                store.clear_all()
            gc.collect()
            torch.mps.empty_cache()
            starts = [len(store.events) for store in stores]
            coordinator = TransitionPrefetchCoordinator(
                stores,
                capsule,
                enabled=condition == "transition_prefetch",
                maximum_cpu_prefetch_bytes=maximum_cpu_prefetch_bytes,
            )
            for layer, store, capacity in zip(layers, stores, capacities, strict=True):
                layer.block_sparse_moe.forward = _predictive_forward(
                    layer.block_sparse_moe, store, coordinator, capacity
                )
            disk_before = _disk_snapshot(args.device)
            result = generate(request["model_input"])
            disk_after = _disk_snapshot(args.device)
            coordinator.close()
            errors = [
                float((observed - expected).abs().max().item())
                for observed, expected in zip(result["scores"], control["scores"], strict=True)
            ]
            activations = [
                event for store, start in zip(stores, starts, strict=True)
                for event in store.events[start:] if event["kind"] == "layer_activation"
            ]
            prefetches = [event for event in coordinator.events if event["kind"] == "transition_prefetch"]
            trials.append({
                "request_number": request_number,
                "case": request["case"],
                "condition_sequence": sequence,
                "condition_order": order,
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
                "prefetched_hits": sum(event["prefetched_hits"] for event in activations),
                "prefetches_issued": len(prefetches),
                "useful_prefetches": sum(len(event["useful_expert_ids"]) for event in prefetches),
                "wasted_prefetches": sum(len(event["wasted_expert_ids"]) for event in prefetches),
                "prefetch_logical_bytes": sum(event["logical_bytes"] for event in prefetches),
                "useful_prefetch_bytes": sum(event["useful_bytes"] for event in prefetches),
                "wasted_prefetch_bytes": sum(event["wasted_bytes"] for event in prefetches),
                "prefetch_worker_seconds": sum(event["worker_seconds"] for event in prefetches),
                "prefetch_wait_seconds": sum(coordinator.wait_seconds),
                "activation_seconds": sum(event["seconds"] for event in activations),
                "peak_mps_bytes": coordinator.peak_mps_bytes,
                "peak_rss_bytes": coordinator.peak_rss_bytes,
                "physical_disk_observation": {
                    "device": args.device,
                    "read_bytes_delta": disk_after["read_bytes"] - disk_before["read_bytes"],
                    "read_count_delta": disk_after["read_count"] - disk_before["read_count"],
                    "system_wide_counter": True,
                    "exclusive_process_attribution": False,
                },
            })

    for control in controls:
        control.pop("scores")
    aggregates = {}
    for condition in CONDITIONS:
        group = [trial for trial in trials if trial["condition"] == condition]
        seconds = [float(trial["seconds"]) for trial in group]
        aggregates[condition] = {
            "sample_count": len(group),
            "median_seconds": statistics.median(seconds),
            "p95_seconds_nearest_rank": _p95(seconds),
            "median_tokens_per_second": statistics.median(
                float(trial["tokens_per_second"]) for trial in group
            ),
            "total_demand_faults": sum(int(trial["demand_faults"]) for trial in group),
            "total_demand_logical_bytes": sum(int(trial["demand_logical_bytes"]) for trial in group),
            "total_useful_prefetch_bytes": sum(int(trial["useful_prefetch_bytes"]) for trial in group),
            "total_wasted_prefetch_bytes": sum(int(trial["wasted_prefetch_bytes"]) for trial in group),
            "total_prefetch_wait_seconds": sum(float(trial["prefetch_wait_seconds"]) for trial in group),
            "median_activation_seconds": statistics.median(
                float(trial["activation_seconds"]) for trial in group
            ),
            "maximum_peak_mps_bytes": max(int(trial["peak_mps_bytes"]) for trial in group),
            "maximum_peak_rss_bytes": max(int(trial["peak_rss_bytes"]) for trial in group),
            "all_outputs_exact": all(
                trial["token_ids_exact_match"] and trial["all_step_logits_exact_match"]
                for trial in group
            ),
        }
    baseline = aggregates["demand_only"]
    candidate = aggregates["transition_prefetch"]
    median_improvement = 100.0 * (1.0 - candidate["median_seconds"] / baseline["median_seconds"])
    gates = {
        "all_tokens_and_logits_exact": all(
            trial["token_ids_exact_match"] and trial["all_step_logits_exact_match"]
            for trial in trials
        ),
        "balanced_condition_order": all(
            sum(
                trial["condition_sequence"] == 0 and trial["condition"] == condition
                for trial in trials
            ) == len(requests) // 2
            for condition in CONDITIONS
        ),
        "controller_memory_within_declared_ceiling": (
            memory_plan.estimated_resident_bytes <= memory_plan.maximum_resident_bytes
        ),
        "useful_prefetch_bytes_exceed_wasted": (
            candidate["total_useful_prefetch_bytes"] > candidate["total_wasted_prefetch_bytes"]
        ),
        "demand_faults_fall": candidate["total_demand_faults"] < baseline["total_demand_faults"],
        "median_improves": candidate["median_seconds"] < baseline["median_seconds"],
        "p95_does_not_regress": (
            candidate["p95_seconds_nearest_rank"] <= baseline["p95_seconds_nearest_rank"]
        ),
        "cold_warm_separation_complete": False,
    }
    screening_gates = {key: value for key, value in gates.items() if key != "cold_warm_separation_complete"}
    report = {
        "schema_version": "aion.transition_prefetch_experiment.v1",
        "run_id": args.run_id,
        "storage_root": str(root),
        "paths": {**{name: str(path) for name, path in paths.items()}, "route_capsule": str(capsule_path)},
        "hashes": {
            **{name: _sha256(path) for name, path in paths.items() if path.is_file()},
            "route_capsule": _sha256(capsule_path),
        },
        "method": {
            "prompt_count": len(requests),
            "generated_tokens_per_trial": args.generated_tokens,
            "conditions": CONDITIONS,
            "balanced_order": True,
            "same_model_load": True,
            "one_layer_ahead_only": True,
            "prefill_prediction_enabled": False,
            "maximum_cpu_prefetch_bytes": maximum_cpu_prefetch_bytes,
            "cache_condition": "warm_uncontrolled",
            "cold_condition_measured": False,
            "p95_method": "nearest_rank",
        },
        "capacity_source": {
            "maximum_resident_bytes": memory_plan.maximum_resident_bytes,
            "estimated_resident_bytes": memory_plan.estimated_resident_bytes,
            "capacities_by_layer": capacities,
            "plan_sha256": memory_plan.plan_sha256,
        },
        "route_capsule": {
            "capsule_sha256": capsule["capsule_sha256"],
            "training_observation_sha256s": observation_sha256s,
            "confidence_threshold": args.confidence_threshold,
            "max_predictions_per_layer": args.max_predictions_per_layer,
        },
        "requests": requests,
        "controls": controls,
        "trials": trials,
        "aggregates": aggregates,
        "comparison": {
            "median_time_improvement_percent": median_improvement,
            "screening_gates": screening_gates,
            "warm_screening_passed": all(screening_gates.values()),
            "full_promotion_gates": gates,
            "promotion_eligible": all(gates.values()),
        },
        "timing": {"checkpoint_load_seconds": checkpoint_load_seconds},
        "memory": {"unrestricted": unrestricted_memory, "experts_removed": stripped_memory},
        "integrity": {
            "all_32_layer_packs_verified": len(stores) == 32,
            "all_1280_experts_addressable": sum(len(store.verified) for store in stores) == 1280,
            "all_artifacts_on_external_storage": all(root in path.parents for path in (*paths.values(), output, capsule_path)),
            "all_trials_exact": gates["all_tokens_and_logits_exact"],
            "memory_ceiling_passed": gates["controller_memory_within_declared_ceiling"],
        },
        "claim_boundary": (
            "Four balanced 24-token prompts under warm uncontrolled filesystem state. The route "
            "capsule is a compact meaning/control artifact, not a weight-compression mechanism. "
            "Disk counters are system-wide. A positive warm screen is not promotion until a "
            "separate cold condition also passes every integrity and performance gate."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "report_sha256": report["report_sha256"],
        "route_capsule": report["route_capsule"],
        "aggregates": aggregates,
        "comparison": report["comparison"],
        "integrity": report["integrity"],
    }, indent=2))
    return 0 if all(report["integrity"].values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
