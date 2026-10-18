#!/usr/bin/env python3
"""Compare dynamic expert tensors with a bounded persistent per-layer Metal arena."""

from __future__ import annotations

import argparse
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
    select_frequency_retention,
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


CONDITION_ORDER = ("dynamic", "persistent_arena", "persistent_arena", "dynamic")
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
    if not values:
        raise ValueError("p95 requires observations")
    return max(values)


class PersistentMetalArenaStore(TimedPackedLayerStore):
    """Per-layer fixed MPS buffers with transient overflow outside retained slots."""

    def __init__(
        self,
        layer: int,
        index: dict[str, Any],
        pack: dict[str, Any],
        capacity: int,
        input_shape: tuple[int, ...],
        output_shape: tuple[int, ...],
        device: torch.device,
        dtype: torch.dtype,
    ) -> None:
        super().__init__(layer, index, pack, transfer_mode="blocking")
        if capacity < 1:
            raise ValueError("arena capacity must be positive")
        self.capacity = capacity
        self.arena_input = torch.empty((capacity, *input_shape), device=device, dtype=dtype)
        self.arena_output = torch.empty((capacity, *output_shape), device=device, dtype=dtype)
        self.expert_to_slot: dict[int, int] = {}
        self.slot_to_expert: dict[int, int] = {}
        self.desired_retained: set[int] = set()
        self.arena_bytes = (
            self.arena_input.numel() * self.arena_input.element_size()
            + self.arena_output.numel() * self.arena_output.element_size()
        )

    def prepare_routes(
        self,
        routes: tuple[tuple[int, ...], ...],
        required: tuple[int, ...],
        capacity: int,
    ) -> None:
        if capacity != self.capacity:
            raise RuntimeError("arena capacity/controller capacity mismatch")
        desired, self.usage_clock = select_frequency_retention(
            routes,
            set(self.expert_to_slot).union(required),
            self.usage_counts,
            self.last_used,
            self.usage_clock,
            capacity,
        )
        self.desired_retained = set(desired)
        for expert in tuple(self.expert_to_slot):
            if expert not in self.desired_retained:
                slot = self.expert_to_slot.pop(expert)
                del self.slot_to_expert[slot]

    def activate_timed(
        self,
        experts: tuple[int, ...],
        device: torch.device,
        dtype: torch.dtype,
    ) -> tuple[dict[int, tuple[torch.Tensor, torch.Tensor]], dict[str, Any]]:
        total_started = time.perf_counter()
        lookup_started = time.perf_counter()
        arena_hits = 0
        demand_experts: list[int] = []
        for expert in experts:
            slot = self.expert_to_slot.get(expert)
            if slot is None:
                demand_experts.append(expert)
            else:
                self.active[expert] = (self.arena_input[slot], self.arena_output[slot])
                arena_hits += 1
        lookup_seconds = time.perf_counter() - lookup_started

        read_started = time.perf_counter()
        cpu_weights = self._load_cpu_many(tuple(demand_experts))
        storage_read_seconds = time.perf_counter() - read_started

        transfer_started = time.perf_counter()
        arena_slot_writes = 0
        transient_experts = 0
        for expert in demand_experts:
            input_weight, output_weight = cpu_weights[expert]
            if expert in self.desired_retained:
                free_slots = set(range(self.capacity)).difference(self.slot_to_expert)
                if not free_slots:
                    raise RuntimeError("bounded arena has no free retained slot")
                slot = min(free_slots)
                self.arena_input[slot].copy_(input_weight)
                self.arena_output[slot].copy_(output_weight)
                self.expert_to_slot[expert] = slot
                self.slot_to_expert[slot] = expert
                self.active[expert] = (self.arena_input[slot], self.arena_output[slot])
                arena_slot_writes += 1
            else:
                self.active[expert] = (
                    input_weight.to(device=device, dtype=dtype),
                    output_weight.to(device=device, dtype=dtype),
                )
                transient_experts += 1
        transfer_enqueue_seconds = time.perf_counter() - transfer_started
        sync_started = time.perf_counter()
        torch.mps.synchronize()
        transfer_sync_seconds = time.perf_counter() - sync_started
        event = {
            "kind": "timed_layer_activation",
            "layer": self.layer,
            "required_experts": len(experts),
            "retained_hits": arena_hits,
            "arena_hits": arena_hits,
            "prefetched_hits": 0,
            "demand_faults": len(demand_experts),
            "demand_logical_bytes": sum(
                int(self.entries[expert]["bytes"]) for expert in demand_experts
            ),
            "lookup_seconds": lookup_seconds,
            "storage_read_seconds": storage_read_seconds,
            "transfer_enqueue_seconds": transfer_enqueue_seconds,
            "transfer_sync_seconds": transfer_sync_seconds,
            "transfer_operations": 2 * len(demand_experts),
            "arena_slot_writes": arena_slot_writes,
            "transient_experts": transient_experts,
            "total_seconds": time.perf_counter() - total_started,
        }
        self.events.append(event)
        return self.active, event

    def release_with_frequency_capacity(
        self,
        routes: tuple[tuple[int, ...], ...],
        capacity: int,
    ) -> None:
        # prepare_routes already applied the identical policy before loading.
        if capacity != self.capacity or not self.desired_retained.issuperset(self.expert_to_slot):
            raise RuntimeError("arena retention state is inconsistent")
        self.active.clear()
        self.retained.clear()
        with self._lock:
            self.cpu_prefetch.clear()

    def reset_trial(self) -> None:
        super().clear_all()
        self.expert_to_slot.clear()
        self.slot_to_expert.clear()
        self.desired_retained.clear()

    def close_arena(self) -> None:
        self.reset_trial()
        self.arena_input = None
        self.arena_output = None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--shard-manifest", type=Path, required=True)
    parser.add_argument("--pack-manifest", type=Path, required=True)
    parser.add_argument("--route-corpus", type=Path, required=True)
    parser.add_argument("--memory-budget-gib", type=float, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--generated-tokens", type=int, default=24)
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
        raise SystemExit("generated tokens and memory budget must be positive")
    if not torch.backends.mps.is_available():
        raise SystemExit("Apple Metal/MPS is required")
    _verify_storage_device(root, args.device)

    shards = json.loads(paths["shards"].read_text(encoding="utf-8"))
    packs = json.loads(paths["packs"].read_text(encoding="utf-8"))
    if not all(shards["integrity"].values()) or not all(packs["integrity"].values()):
        raise RuntimeError("manifest integrity gate failed")
    if packs["source_manifest_sha256"] != _sha256(paths["shards"]):
        raise RuntimeError("pack/source manifest binding failed")

    indexes: list[dict[str, Any]] = []
    entries_by_layer: list[dict[int, dict[str, Any]]] = []
    for number, shard_layer in enumerate(shards["layers"]):
        index_path = Path(shard_layer["index_path"])
        if root not in index_path.resolve().parents or _sha256(index_path) != shard_layer["index_sha256"]:
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
    shapes = []
    dynamic_stores: list[TimedPackedLayerStore] = []
    for number, (layer, index, pack_layer) in enumerate(
        zip(layers, indexes, packs["layers"], strict=True)
    ):
        moe = layer.block_sparse_moe
        shapes.append((
            tuple(moe.input_linear.weight.shape[1:]),
            tuple(moe.output_linear.weight.shape[1:]),
            moe.input_linear.weight.dtype,
        ))
        store = TimedPackedLayerStore(number, index, pack_layer, transfer_mode="blocking")
        store.preverify(root)
        dynamic_stores.append(store)
        moe.input_linear = None
        moe.output_linear = None
    gc.collect()
    torch.mps.empty_cache()
    stripped_memory = _memory_snapshot("expert_tensors_removed")

    arena_stores: list[PersistentMetalArenaStore] | None = None
    arena_allocation_seconds = 0.0
    arena_allocated_bytes = 0
    trials: list[dict[str, Any]] = []
    for sequence, condition in enumerate(CONDITION_ORDER):
        if condition == "persistent_arena" and arena_stores is None:
            started = time.perf_counter()
            arena_stores = [
                PersistentMetalArenaStore(
                    number, index, pack_layer, capacity,
                    shapes[number][0], shapes[number][1], torch.device("mps"), shapes[number][2],
                )
                for number, (index, pack_layer, capacity) in enumerate(
                    zip(indexes, packs["layers"], capacities, strict=True)
                )
            ]
            torch.mps.synchronize()
            arena_allocation_seconds = time.perf_counter() - started
            arena_allocated_bytes = sum(store.arena_bytes for store in arena_stores)
            for source, arena in zip(dynamic_stores, arena_stores, strict=True):
                arena.verified = set(source.verified)
        if condition == "dynamic" and sequence == 3 and arena_stores is not None:
            for store in arena_stores:
                store.close_arena()
            arena_stores = None
            gc.collect()
            torch.mps.empty_cache()

        stores = dynamic_stores if condition == "dynamic" else arena_stores
        if stores is None:
            raise RuntimeError("arena stores were not allocated")
        for store in stores:
            if isinstance(store, PersistentMetalArenaStore):
                store.reset_trial()
            else:
                store.clear_all()
        gc.collect()
        if condition == "dynamic":
            torch.mps.empty_cache()
        event_starts = [len(store.events) for store in stores]
        stage_seconds = {name: 0.0 for name in STAGE_NAMES}
        coordinator = LayerAheadCoordinator(stores, tuple(() for _ in stores))
        for layer, store, capacity in zip(layers, stores, capacities, strict=True):
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
            event for store, start in zip(stores, event_starts, strict=True)
            for event in store.events[start:] if event["kind"] == "timed_layer_activation"
        ]
        attribution = summarize_stage_seconds(stage_seconds, result["seconds"])
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
            "arena_slot_writes": sum(event.get("arena_slot_writes", 0) for event in activations),
            "transient_experts": sum(event.get("transient_experts", 0) for event in activations),
            "pack_open_operations": sum(event["demand_faults"] > 0 for event in activations),
            "metal_transfer_operations": sum(event["transfer_operations"] for event in activations),
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

    control.pop("scores")
    aggregates: dict[str, dict[str, Any]] = {}
    for condition in ("dynamic", "persistent_arena"):
        group = [trial for trial in trials if trial["condition"] == condition]
        seconds = [float(trial["seconds"]) for trial in group]
        aggregates[condition] = {
            "sample_count": len(group),
            "median_seconds": statistics.median(seconds),
            "p95_seconds_nearest_rank": _p95(seconds),
            "median_tokens_per_second": statistics.median(
                float(trial["tokens_per_second"]) for trial in group
            ),
            "median_metal_transfer_seconds": statistics.median(
                float(trial["attribution"]["stage_seconds"]["metal_transfer_enqueue"])
                for trial in group
            ),
            "total_demand_logical_bytes": sum(int(trial["demand_logical_bytes"]) for trial in group),
            "total_demand_faults": sum(int(trial["demand_faults"]) for trial in group),
            "maximum_peak_mps_bytes": max(int(trial["peak_mps_bytes"]) for trial in group),
            "all_tokens_exact": all(bool(trial["token_ids_exact_match"]) for trial in group),
            "all_logits_exact": all(bool(trial["all_step_logits_exact_match"]) for trial in group),
            "minimum_attributed_percent": min(
                float(trial["attribution"]["attributed_percent"]) for trial in group
            ),
        }
    dynamic = aggregates["dynamic"]
    arena = aggregates["persistent_arena"]
    median_improvement = 100.0 * (1.0 - arena["median_seconds"] / dynamic["median_seconds"])
    metal_improvement = 100.0 * (
        1.0 - arena["median_metal_transfer_seconds"] / dynamic["median_metal_transfer_seconds"]
    )
    gates = {
        "complete_abba_order": tuple(trial["condition"] for trial in trials) == CONDITION_ORDER,
        "all_tokens_exact": all(trial["token_ids_exact_match"] for trial in trials),
        "all_step_logits_exact": all(trial["all_step_logits_exact_match"] for trial in trials),
        "all_runs_at_least_95_percent_attributed": all(
            trial["attribution"]["attributed_percent"] >= 95.0 for trial in trials
        ),
        "arena_allocation_within_declared_ceiling": (
            arena_allocated_bytes <= memory_plan.maximum_resident_bytes
        ),
        "arena_logical_demand_not_higher": (
            arena["total_demand_logical_bytes"] <= dynamic["total_demand_logical_bytes"]
        ),
        "arena_p95_not_higher": arena["p95_seconds_nearest_rank"] <= dynamic["p95_seconds_nearest_rank"],
        "median_live_time_improves_at_least_10_percent": median_improvement >= 10.0,
    }
    report = {
        "schema_version": "aion.moe_metal_arena_abba.v1",
        "run_id": args.run_id,
        "storage_root": str(root),
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": {name: _sha256(path) for name, path in paths.items() if path.is_file()},
        "method": {
            "prompt": args.prompt,
            "prompt_count": 1,
            "generated_tokens_per_trial": args.generated_tokens,
            "condition_order": CONDITION_ORDER,
            "same_model_load": True,
            "empty_expert_mapping_before_each_trial": True,
            "persistent_arena_allocated_once_for_b_pair": True,
            "cache_condition": "warm_uncontrolled",
            "p95_method": "nearest_rank_max_for_n2",
            "stage_boundary_synchronization": True,
        },
        "capacity_source": {
            "kind": "route_corpus_byte_ceiling",
            "observation_sha256s": observation_sha256s,
            "maximum_resident_bytes": memory_plan.maximum_resident_bytes,
            "estimated_resident_bytes": memory_plan.estimated_resident_bytes,
            "plan_sha256": memory_plan.plan_sha256,
            "capacities_by_layer": capacities,
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
            "arena_median_time_improvement_percent": median_improvement,
            "arena_median_metal_time_improvement_percent": metal_improvement,
            "promotion_gates": gates,
            "promotion_eligible": all(gates.values()),
        },
        "timing": {
            "checkpoint_load_seconds": checkpoint_load_seconds,
            "arena_one_time_allocation_seconds": arena_allocation_seconds,
        },
        "memory": {
            "unrestricted": unrestricted_memory,
            "experts_removed": stripped_memory,
            "arena_allocated_bytes": arena_allocated_bytes,
        },
        "integrity": {
            "all_32_layer_packs_verified": len(dynamic_stores) == 32,
            "all_1280_experts_addressable": sum(len(store.verified) for store in dynamic_stores) == 1280,
            "all_artifacts_on_external_storage": all(root in path.parents for path in (*paths.values(), output)),
            "all_trials_exact": gates["all_tokens_exact"] and gates["all_step_logits_exact"],
            "memory_ceiling_passed": gates["arena_allocation_within_declared_ceiling"],
        },
        "claim_boundary": (
            "One prompt with two observations per condition under warm uncontrolled filesystem state. "
            "The arena reuses fixed retained slots but still permits transient current-layer overflow. "
            "Stage synchronizations perturb latency and disk counters are system-wide. Promotion requires "
            "all declared gates; otherwise this is diagnostic evidence only."
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
        "memory": report["memory"],
        "integrity": report["integrity"],
    }, indent=2))
    return 0 if all(report["integrity"].values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
