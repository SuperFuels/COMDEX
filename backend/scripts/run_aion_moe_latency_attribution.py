#!/usr/bin/env python3
"""Attribute the full SD-backed MoE token-generation critical path."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import gc
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any

import psutil
import torch
import torch.nn.functional as functional
from transformers import AutoModelForCausalLM, AutoTokenizer

from backend.modules.aion_inference import (
    AdaptiveInferenceRuntime,
    ExpertRouteCorpus,
    verify_promoted_expert_cache_plan,
)
from backend.scripts.run_aion_layer_pack_experiment import PackedLayerScopedStore
from backend.scripts.run_aion_layer_scoped_moe_experiment import (
    LayerAheadCoordinator,
    _chat_tokens,
)
from backend.scripts.run_aion_moe_end_to_end_fault_in import _memory_snapshot, _sha256


DEFAULT_PROMPT = (
    "Explain how to handle a refund request when approval is required and no "
    "irreversible action is allowed."
)


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def summarize_stage_seconds(
    stage_seconds: dict[str, float], total_seconds: float
) -> dict[str, Any]:
    if total_seconds <= 0 or any(value < 0 for value in stage_seconds.values()):
        raise ValueError("timing values must be non-negative and total must be positive")
    attributed = sum(stage_seconds.values())
    unassigned = max(0.0, total_seconds - attributed)
    return {
        "stage_seconds": stage_seconds,
        "stage_percent_of_total": {
            name: 100.0 * value / total_seconds for name, value in stage_seconds.items()
        },
        "attributed_seconds": attributed,
        "attributed_percent": min(100.0, 100.0 * attributed / total_seconds),
        "unassigned_seconds": unassigned,
        "unassigned_percent": 100.0 * unassigned / total_seconds,
    }


def _disk_snapshot(device: str) -> dict[str, int]:
    counters = psutil.disk_io_counters(perdisk=True)
    if device not in counters:
        raise RuntimeError(f"disk counter unavailable for {device}")
    value = counters[device]
    return {"read_bytes": int(value.read_bytes), "read_count": int(value.read_count)}


def _verify_storage_device(storage_root: Path, device: str) -> str:
    """Bind physical-I/O evidence to the whole disk containing storage_root."""
    completed = subprocess.run(
        ["df", "-P", str(storage_root)],
        check=True,
        capture_output=True,
        text=True,
    )
    lines = completed.stdout.strip().splitlines()
    if len(lines) < 2:
        raise RuntimeError("unable to resolve storage-root device")
    partition = Path(lines[-1].split()[0]).name
    match = re.fullmatch(r"(disk\d+)(?:s\d+)+", partition)
    observed = match.group(1) if match else partition
    if observed != device:
        raise RuntimeError(
            f"disk counter {device!r} does not belong to storage root; expected {observed!r}"
        )
    return observed


class TimedPackedLayerStore(PackedLayerScopedStore):
    """Packed store with non-overlapping lookup, read and Metal-transfer timing."""

    def __init__(
        self,
        layer: int,
        index: dict[str, Any],
        pack: dict[str, Any],
        *,
        transfer_mode: str = "blocking",
        expert_compute_device: str = "mps",
    ) -> None:
        super().__init__(layer, index, pack)
        if transfer_mode not in {
            "blocking", "non_blocking", "fused_blocking", "parallel_materialized"
        }:
            raise ValueError("unsupported transfer mode")
        self.transfer_mode = transfer_mode
        if expert_compute_device not in {"mps", "cpu", "phase_aware_cpu_faults"}:
            raise ValueError("unsupported expert compute device")
        self.expert_compute_device = expert_compute_device
        self.current_sequence_length = 0
        self.materialize_executor: ThreadPoolExecutor | None = None

    def activate_timed(
        self,
        experts: tuple[int, ...],
        device: torch.device,
        dtype: torch.dtype,
    ) -> tuple[dict[int, tuple[torch.Tensor, torch.Tensor]], dict[str, Any]]:
        total_started = time.perf_counter()
        lookup_started = time.perf_counter()
        retained_hits = 0
        prefetched_hits = 0
        demand_experts = []
        cpu_for_transfer: dict[int, tuple[torch.Tensor, torch.Tensor]] = {}
        for expert in experts:
            retained = self.retained.get(expert)
            if retained is not None:
                self.active[expert] = retained
                retained_hits += 1
                continue
            with self._lock:
                prefetched = self.cpu_prefetch.pop(expert, None)
            if prefetched is None:
                demand_experts.append(expert)
            else:
                cpu_for_transfer[expert] = prefetched
                prefetched_hits += 1
        lookup_seconds = time.perf_counter() - lookup_started

        read_started = time.perf_counter()
        cpu_for_transfer.update(self._load_cpu_many(tuple(demand_experts)))
        storage_read_seconds = time.perf_counter() - read_started

        materialize_started = time.perf_counter()
        if self.transfer_mode == "parallel_materialized" and cpu_for_transfer:
            if self.materialize_executor is None:
                raise RuntimeError("parallel materialization executor is not configured")

            def clone_pair(pair):
                return tuple(
                    value.clone(memory_format=torch.contiguous_format) for value in pair
                )

            pairs = self.materialize_executor.map(clone_pair, cpu_for_transfer.values())
            cpu_for_transfer = dict(zip(cpu_for_transfer, pairs, strict=True))
        cpu_materialization_seconds = time.perf_counter() - materialize_started

        cpu_fault_execution = (
            self.expert_compute_device == "cpu"
            or (
                self.expert_compute_device == "phase_aware_cpu_faults"
                and self.current_sequence_length == 1
            )
        )
        if cpu_fault_execution:
            materialize_started = time.perf_counter()
            cpu_for_transfer = {
                expert: tuple(value.to(dtype=dtype) for value in pair)
                for expert, pair in cpu_for_transfer.items()
            }
            cpu_materialization_seconds += time.perf_counter() - materialize_started

        transfer_started = time.perf_counter()
        transfer_operations = 0
        for expert, cpu_weights in cpu_for_transfer.items():
            if cpu_fault_execution:
                self.active[expert] = cpu_weights
            elif self.transfer_mode == "fused_blocking":
                input_weight, output_weight = cpu_weights
                input_elements = input_weight.numel()
                fused = torch.cat((input_weight.reshape(-1), output_weight.reshape(-1)))
                transferred = fused.to(device=device, dtype=dtype)
                self.active[expert] = (
                    transferred[:input_elements].view(input_weight.shape),
                    transferred[input_elements:].view(output_weight.shape),
                )
                transfer_operations += 1
            else:
                non_blocking = self.transfer_mode == "non_blocking"
                self.active[expert] = (
                    cpu_weights[0].to(
                        device=device, dtype=dtype, non_blocking=non_blocking
                    ),
                    cpu_weights[1].to(
                        device=device, dtype=dtype, non_blocking=non_blocking
                    ),
                )
                transfer_operations += 2
        transfer_enqueue_seconds = time.perf_counter() - transfer_started
        sync_started = time.perf_counter()
        if not cpu_fault_execution:
            torch.mps.synchronize()
        transfer_sync_seconds = time.perf_counter() - sync_started
        event = {
            "kind": "timed_layer_activation",
            "layer": self.layer,
            "required_experts": len(experts),
            "retained_hits": retained_hits,
            "prefetched_hits": prefetched_hits,
            "demand_faults": len(demand_experts),
            "demand_logical_bytes": sum(
                int(self.entries[expert]["bytes"]) for expert in demand_experts
            ),
            "lookup_seconds": lookup_seconds,
            "storage_read_seconds": storage_read_seconds,
            "cpu_materialization_seconds": cpu_materialization_seconds,
            "transfer_enqueue_seconds": transfer_enqueue_seconds,
            "transfer_sync_seconds": transfer_sync_seconds,
            "transfer_operations": transfer_operations,
            "cpu_fault_experts": len(cpu_for_transfer) if cpu_fault_execution else 0,
            "metal_fault_experts": 0 if cpu_fault_execution else len(cpu_for_transfer),
            "total_seconds": time.perf_counter() - total_started,
        }
        self.events.append(event)
        return self.active, event


def _timed_forward(block, store, coordinator, capacity: int, stage_seconds: dict[str, float]):
    router = block.router
    activation = block.activation
    input_size = block.input_size

    def forward(layer_input):
        started = time.perf_counter()
        torch.mps.synchronize()
        stage_seconds["shared_and_interlayer_sync"] += time.perf_counter() - started

        started = time.perf_counter()
        batch_size, length, embedding_size = layer_input.size()
        store.current_sequence_length = length
        flattened = layer_input.reshape(-1, embedding_size)
        _, batch_index, batch_gates, expert_size, router_logits = router(flattened)
        observed_routes = tuple(
            tuple(sorted(row.topk(router.top_k, dim=-1).indices.tolist()))
            for row in router_logits
        )
        store.route_batches.append(observed_routes)
        torch.mps.synchronize()
        stage_seconds["router_and_route_capture"] += time.perf_counter() - started

        started = time.perf_counter()
        expert_inputs = flattened[batch_index]
        input_list = expert_inputs.split(expert_size, dim=0)
        required = tuple(expert for expert, value in enumerate(input_list) if value.shape[0])
        torch.mps.synchronize()
        stage_seconds["expert_dispatch"] += time.perf_counter() - started

        prepare_routes = getattr(store, "prepare_routes", None)
        if prepare_routes is not None:
            started = time.perf_counter()
            prepare_routes(observed_routes, required, capacity)
            stage_seconds["cache_policy_and_eviction"] += time.perf_counter() - started

        weights, activation_event = store.activate_timed(
            required, layer_input.device, layer_input.dtype
        )
        for source, target in (
            ("lookup_seconds", "cache_lookup"),
            ("storage_read_seconds", "storage_and_safetensors_read"),
            ("cpu_materialization_seconds", "cpu_page_materialization"),
            ("transfer_enqueue_seconds", "metal_transfer_enqueue"),
            ("transfer_sync_seconds", "metal_transfer_sync"),
        ):
            stage_seconds[target] += activation_event[source]
        coordinator.observe_memory()

        started = time.perf_counter()
        cpu_experts = {
            expert for expert in required if weights[expert][0].device.type == "cpu"
        }
        cpu_input_list = (
            expert_inputs.to(device="cpu", dtype=layer_input.dtype).split(
                expert_size, dim=0
            )
            if cpu_experts else None
        )
        output_list: list[torch.Tensor | None] = []
        cpu_outputs: list[tuple[int, torch.Tensor]] = []
        for expert, expert_input in enumerate(input_list):
            if expert_input.shape[0] == 0:
                output_list.append(torch.empty(
                    (0, input_size), dtype=layer_input.dtype, device=layer_input.device
                ))
                continue
            compute_input = (
                cpu_input_list[expert] if expert in cpu_experts else expert_input
            )
            input_weight, output_weight = weights[expert]
            hidden = functional.linear(compute_input, input_weight)
            gate_half, value_half = hidden.chunk(2, dim=-1)
            output = functional.linear(activation(gate_half) * value_half, output_weight)
            if expert in cpu_experts:
                cpu_outputs.append((expert, output))
                output_list.append(None)
            else:
                output_list.append(output)
        if cpu_outputs:
            cpu_batch = torch.cat([value for _, value in cpu_outputs], dim=0).to(
                layer_input.device
            )
            sizes = [value.shape[0] for _, value in cpu_outputs]
            for (expert, _), value in zip(
                cpu_outputs, cpu_batch.split(sizes, dim=0), strict=True
            ):
                output_list[expert] = value
        if any(value is None for value in output_list):
            raise RuntimeError("CPU expert output assembly failed")
        expert_outputs = torch.cat(output_list, dim=0)
        expert_outputs = expert_outputs * batch_gates[:, None]
        zeros = torch.zeros(
            (batch_size * length, input_size),
            dtype=expert_outputs.dtype,
            device=expert_outputs.device,
        )
        result = zeros.index_add(0, batch_index, expert_outputs).view(
            batch_size, length, input_size
        )
        torch.mps.synchronize()
        stage_seconds["expert_compute_and_combine"] += time.perf_counter() - started

        started = time.perf_counter()
        store.release_with_frequency_capacity(observed_routes, capacity)
        stage_seconds["cache_policy_and_eviction"] += time.perf_counter() - started
        return result

    return forward


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--shard-manifest", type=Path, required=True)
    parser.add_argument("--pack-manifest", type=Path, required=True)
    parser.add_argument(
        "--route-source-pack-manifest", type=Path,
        help="Original pack manifest bound by the route corpus when execution uses a derived pack.",
    )
    parser.add_argument("--cache-plan", type=Path)
    parser.add_argument("--route-corpus", type=Path)
    parser.add_argument("--memory-budget-gib", type=float)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--device", required=True, help="Whole-disk counter, for example disk6")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--generated-tokens", type=int, default=8)
    parser.add_argument(
        "--cache-condition",
        choices=("warm_uncontrolled",),
        default="warm_uncontrolled",
        help="Explicit cache label; this stage does not claim privileged OS-cache eviction",
    )
    parser.add_argument(
        "--expert-compute-device",
        choices=("mps", "cpu", "phase_aware_cpu_faults"), default="mps",
        help="Run experts on Metal, CPU, or send only decode-time faults to CPU.",
    )
    parser.add_argument(
        "--zstd-decode-workers", type=int,
        help="Bounded parallel decoder count for compressed expert packs.",
    )
    parser.add_argument(
        "--transfer-mode",
        choices=("blocking", "non_blocking", "fused_blocking"),
        default="blocking",
        help="Whether individual CPU-to-Metal tensor copies may enqueue asynchronously",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.storage_root.resolve()
    if (args.route_corpus is None) != (args.memory_budget_gib is None):
        raise SystemExit("route-corpus and memory-budget-gib must be supplied together")
    if args.cache_plan is None and args.route_corpus is None:
        raise SystemExit("provide cache-plan or a route-corpus memory budget")
    if args.cache_plan is not None and args.route_corpus is not None:
        raise SystemExit("choose cache-plan or route-corpus memory budget, not both")
    paths = {
        "model": args.model_path.resolve(),
        "shards": args.shard_manifest.resolve(),
        "packs": args.pack_manifest.resolve(),
    }
    if args.route_source_pack_manifest is not None:
        paths["route_source_packs"] = args.route_source_pack_manifest.resolve()
    if args.cache_plan is not None:
        paths["cache_plan"] = args.cache_plan.resolve()
    if args.route_corpus is not None:
        paths["route_corpus"] = args.route_corpus.resolve()
    output = (args.output or root / "experiments" / f"{args.run_id}.json").resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all artifacts must reside on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    if args.generated_tokens < 1:
        raise SystemExit("generated-tokens must be positive")
    if args.zstd_decode_workers is not None and args.zstd_decode_workers < 2:
        raise SystemExit("zstd decode workers must be at least two")
    if not torch.backends.mps.is_available():
        raise SystemExit("Apple Metal/MPS is required")
    _verify_storage_device(root, args.device)

    shards = json.loads(paths["shards"].read_text(encoding="utf-8"))
    packs = json.loads(paths["packs"].read_text(encoding="utf-8"))
    if not all(shards["integrity"].values()) or not all(packs["integrity"].values()):
        raise RuntimeError("manifest integrity gate failed")
    indexes = []
    entries_by_layer = []
    for number, shard_layer in enumerate(shards["layers"]):
        index_path = Path(shard_layer["index_path"])
        if root not in index_path.resolve().parents or _sha256(index_path) != shard_layer["index_sha256"]:
            raise RuntimeError(f"index integrity failed: layer {number}")
        index = json.loads(index_path.read_text(encoding="utf-8"))
        indexes.append(index)
        entries_by_layer.append({int(entry["expert"]): entry for entry in index["experts"]})

    capacity_source: dict[str, Any]
    if args.route_corpus is not None:
        corpus = ExpertRouteCorpus(paths["route_corpus"])
        observation_sha256s = tuple(sorted(path.stem for path in corpus.objects.glob("*.json")))
        if not observation_sha256s:
            raise RuntimeError("route corpus contains no observations")
        route_pack_path = paths.get("route_source_packs", paths["packs"])
        expected_bindings = {
            "model_config_sha256": _sha256(paths["model"] / "config.json"),
            "shard_manifest_sha256": _sha256(paths["shards"]),
            "pack_manifest_sha256": _sha256(route_pack_path),
        }
        if corpus.load(observation_sha256s[0])["bindings"] != expected_bindings:
            raise RuntimeError("route corpus does not bind the selected model and manifests")
        if "route_source_packs" in paths:
            if packs.get("source_manifest_sha256") != _sha256(paths["shards"]):
                raise RuntimeError("derived execution pack is not bound to the expert shards")
        memory_plan = corpus.optimize_memory(
            observation_sha256s,
            entries_by_layer,
            maximum_resident_bytes=int(args.memory_budget_gib * 1024**3),
        )
        capacities = memory_plan.capacities_by_layer
        capacity_source = {
            "kind": "route_corpus_byte_ceiling",
            "observation_sha256s": observation_sha256s,
            "maximum_resident_bytes": memory_plan.maximum_resident_bytes,
            "estimated_resident_bytes": memory_plan.estimated_resident_bytes,
            "plan_sha256": memory_plan.plan_sha256,
        }
    else:
        plan_document = json.loads(paths["cache_plan"].read_text(encoding="utf-8"))
        capacities = verify_promoted_expert_cache_plan(
            plan_document,
            expected_model_config_sha256=_sha256(paths["model"] / "config.json"),
            expected_shard_manifest_sha256=_sha256(paths["shards"]),
            expected_pack_manifest_sha256=_sha256(paths["packs"]),
        )
        capacity_source = {
            "kind": "promoted_cache_plan",
            "artifact_sha256": plan_document["artifact_sha256"],
        }

    evidence_root = root / "runtime-evidence" / args.run_id
    runtime = AdaptiveInferenceRuntime(
        replay_path=evidence_root / "replay.sqlite3",
        trace_path=evidence_root / "trace.jsonl",
    )
    routed = runtime.route(args.prompt)
    if not routed.model_call_required or not routed.fallback_prompt:
        raise RuntimeError("attribution prompt did not reach model fallback")

    load_started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(paths["model"], local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        paths["model"], local_files_only=True, dtype=torch.float16,
        device_map={"": "mps"}, low_cpu_mem_usage=True,
    ).eval()
    checkpoint_load_seconds = time.perf_counter() - load_started

    def generate() -> dict[str, Any]:
        inputs = _chat_tokens(tokenizer, routed.fallback_prompt)
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
    stores = []
    for number, (layer, index, pack_layer) in enumerate(
        zip(layers, indexes, packs["layers"], strict=True)
    ):
        store = TimedPackedLayerStore(
            number,
            index,
            pack_layer,
            transfer_mode=args.transfer_mode,
            expert_compute_device=args.expert_compute_device,
        )
        store.preverify(root)
        stores.append(store)
        layer.block_sparse_moe.input_linear = None
        layer.block_sparse_moe.output_linear = None
    gc.collect()
    torch.mps.empty_cache()
    stripped_memory = _memory_snapshot("expert_tensors_removed")

    zstd_decode_executor = (
        ThreadPoolExecutor(
            max_workers=args.zstd_decode_workers,
            thread_name_prefix="aion-zstd-decode",
        )
        if args.zstd_decode_workers is not None else None
    )
    for store in stores:
        store.zstd_decode_executor = zstd_decode_executor

    stage_seconds = {
        name: 0.0 for name in (
            "shared_and_interlayer_sync", "router_and_route_capture", "expert_dispatch",
            "cache_lookup", "storage_and_safetensors_read", "cpu_page_materialization",
            "metal_transfer_enqueue",
            "metal_transfer_sync", "expert_compute_and_combine", "cache_policy_and_eviction",
        )
    }
    peak_expert_resident_bytes = 0
    coordinator = LayerAheadCoordinator(stores, tuple(() for _ in stores))
    for layer, store, capacity in zip(layers, stores, capacities, strict=True):
        layer.block_sparse_moe.forward = _timed_forward(
            layer.block_sparse_moe, store, coordinator, capacity, stage_seconds
        )
    disk_before = _disk_snapshot(args.device)
    result = generate()
    peak_expert_resident_bytes = max(
        (
            sum(
                int(store.entries[expert]["bytes"])
                for expert in set(store.active).union(store.retained)
            )
            for store in stores
        ),
        default=0,
    )
    # The generation-end snapshot is a lower bound because layer activations
    # have already been released. Reconstruct the conservative controller peak
    # from the charged slots used by the verified byte-budget planner.
    planned_expert_resident_bytes = sum(
        capacity * max(int(entry["bytes"]) for entry in entries.values())
        for capacity, entries in zip(capacities, entries_by_layer, strict=True)
    )
    peak_expert_resident_bytes = max(
        peak_expert_resident_bytes, planned_expert_resident_bytes
    )
    disk_after = _disk_snapshot(args.device)
    coordinator.close()
    if zstd_decode_executor is not None:
        zstd_decode_executor.shutdown(wait=True)

    errors = [
        float((observed - expected).abs().max().item())
        for observed, expected in zip(result["scores"], control["scores"], strict=True)
    ]
    activations = [
        event for store in stores for event in store.events
        if event["kind"] == "timed_layer_activation"
    ]
    attribution = summarize_stage_seconds(stage_seconds, result["seconds"])
    attribution["instrumentation_warning"] = (
        "Stage-boundary Metal synchronizations make attribution interpretable but perturb runtime; "
        "the uninstrumented reference remains the throughput baseline."
    )
    physical = {
        "device": args.device,
        "read_bytes_delta": disk_after["read_bytes"] - disk_before["read_bytes"],
        "read_count_delta": disk_after["read_count"] - disk_before["read_count"],
        "system_wide_counter": True,
        "exclusive_process_attribution": False,
    }
    control.pop("scores")
    result.pop("scores")
    integrity = {
        "cache_plan_or_corpus_verified_against_model_and_manifests": True,
        "all_32_layer_packs_verified": len(stores) == 32,
        "all_1280_experts_addressable": sum(len(store.verified) for store in stores) == 1280,
        "token_ids_exact_match": result["token_ids"] == control["token_ids"],
        "all_step_logits_exact_match": all(error == 0.0 for error in errors),
        "all_artifacts_on_external_storage": all(root in path.parents for path in (*paths.values(), output)),
        "disk_counters_monotonic": physical["read_bytes_delta"] >= 0 and physical["read_count_delta"] >= 0,
    }
    if args.memory_budget_gib is not None:
        integrity["expert_resident_memory_within_declared_ceiling"] = (
            peak_expert_resident_bytes <= capacity_source["maximum_resident_bytes"]
        )
    report = {
        "schema_version": "aion.moe_latency_attribution.v1",
        "run_id": args.run_id,
        "storage_root": str(root),
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": {name: _sha256(path) for name, path in paths.items() if path.is_file()},
        "method": {
            "prompt": args.prompt, "prompt_count": 1,
            "generated_tokens": args.generated_tokens,
            "cache_capacity": sum(capacities), "stage_boundary_synchronization": True,
            "cache_condition": args.cache_condition,
            "transfer_mode": args.transfer_mode,
            "expert_compute_device": args.expert_compute_device,
            "zstd_decode_workers": args.zstd_decode_workers,
            "os_file_cache_controlled": False,
            "derived_execution_pack_verified": "route_source_packs" in paths,
        },
        "capacity_source": capacity_source,
        "gateway": {
            "glyph_address": routed.glyph_address,
            "model_input_sha256": hashlib.sha256(routed.fallback_prompt.encode()).hexdigest(),
            "proof_receipt_sha256": routed.proof_receipt["proof_receipt_sha256"],
        },
        "control": control,
        "instrumented": {
            **result,
            "tokens_per_second": len(result["token_ids"]) / result["seconds"],
            "maximum_step_logit_error": max(errors, default=0.0),
            "demand_faults": sum(event["demand_faults"] for event in activations),
            "demand_logical_bytes": sum(event["demand_logical_bytes"] for event in activations),
            "retained_hits": sum(event["retained_hits"] for event in activations),
            "pack_open_operations": sum(store.pack_opens for store in stores),
            "metal_transfer_operations": sum(event["transfer_operations"] for event in activations),
        },
        "attribution": attribution,
        "physical_disk_observation": physical,
        "timing": {"checkpoint_load_seconds": checkpoint_load_seconds},
        "timing_summary": {
            "sample_count": 1,
            "generation_seconds_p50": result["seconds"],
            "generation_seconds_p95": result["seconds"],
            "single_sample_percentiles": True,
        },
        "memory": {
            "unrestricted": unrestricted_memory, "experts_removed": stripped_memory,
            "instrumented_peak_mps_bytes": coordinator.peak_mps_bytes,
            "instrumented_peak_rss_bytes": coordinator.peak_rss_bytes,
            "conservative_peak_expert_resident_bytes": peak_expert_resident_bytes,
        },
        "integrity": integrity,
        "claim_boundary": (
            "One warm-cache prompt attributes an instrumented critical path. Disk counters are "
            "system-wide and stage synchronizations perturb timing. This identifies optimization "
            "targets but does not establish population performance or exclusive physical SD bytes."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output), "report_sha256": report["report_sha256"],
        "instrumented": report["instrumented"], "attribution": attribution,
        "physical_disk_observation": physical, "integrity": integrity,
    }, indent=2))
    return 0 if all(integrity.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
