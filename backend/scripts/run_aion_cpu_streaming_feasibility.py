#!/usr/bin/env python3
"""One-token exactness and latency probe for SD-streamed CPU MoE experts."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import time
from typing import Any

import psutil
import torch
import torch.nn.functional as functional
from transformers import AutoModelForCausalLM, AutoTokenizer

from backend.modules.aion_inference import AdaptiveInferenceRuntime, ExpertRouteCorpus
from backend.scripts.run_aion_layer_pack_experiment import PackedLayerScopedStore
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256
from backend.scripts.run_aion_moe_latency_attribution import (
    DEFAULT_PROMPT,
    _canonical_sha256,
    _disk_snapshot,
    _verify_storage_device,
)


def _cpu_memory(label: str) -> dict[str, int | str]:
    process = psutil.Process()
    return {
        "label": label,
        "process_rss_bytes": process.memory_info().rss,
        "system_available_bytes": psutil.virtual_memory().available,
    }


class CpuPackedLayerStore(PackedLayerScopedStore):
    def activate_cpu(
        self,
        experts: tuple[int, ...],
        dtype: torch.dtype,
    ) -> tuple[dict[int, tuple[torch.Tensor, torch.Tensor]], dict[str, Any]]:
        started = time.perf_counter()
        retained_hits = 0
        demand = []
        for expert in experts:
            retained = self.retained.get(expert)
            if retained is None:
                demand.append(expert)
            else:
                self.active[expert] = retained
                retained_hits += 1
        read_started = time.perf_counter()
        loaded = self._load_cpu_many(tuple(demand))
        materialized: dict[int, tuple[torch.Tensor, torch.Tensor]] = {}
        for expert, weights in loaded.items():
            materialized[expert] = tuple(
                weight.to(dtype=dtype)
                if weight.dtype != dtype
                else weight.clone(memory_format=torch.contiguous_format)
                for weight in weights
            )
        read_seconds = time.perf_counter() - read_started
        for expert, weights in materialized.items():
            self.active[expert] = weights
        event = {
            "kind": "cpu_layer_activation",
            "layer": self.layer,
            "required_experts": len(experts),
            "retained_hits": retained_hits,
            "demand_faults": len(demand),
            "demand_logical_bytes": sum(int(self.entries[expert]["bytes"]) for expert in demand),
            "storage_and_decode_seconds": read_seconds,
            "total_seconds": time.perf_counter() - started,
        }
        self.events.append(event)
        return self.active, event


class CpuObserver:
    def __init__(self) -> None:
        self.peak_rss_bytes = 0

    def observe(self) -> None:
        self.peak_rss_bytes = max(self.peak_rss_bytes, psutil.Process().memory_info().rss)


def _cpu_streamed_forward(
    block,
    store: CpuPackedLayerStore,
    observer: CpuObserver,
    capacity: int,
    stage_seconds: dict[str, float],
):
    router = block.router
    activation = block.activation
    input_size = block.input_size

    def forward(layer_input):
        started = time.perf_counter()
        batch_size, length, embedding_size = layer_input.size()
        flattened = layer_input.reshape(-1, embedding_size)
        _, batch_index, batch_gates, expert_size, router_logits = router(flattened)
        observed_routes = tuple(
            tuple(sorted(row.topk(router.top_k, dim=-1).indices.tolist()))
            for row in router_logits
        )
        store.route_batches.append(observed_routes)
        stage_seconds["router_and_route_capture"] += time.perf_counter() - started

        started = time.perf_counter()
        expert_inputs = flattened[batch_index]
        input_list = expert_inputs.split(expert_size, dim=0)
        required = tuple(expert for expert, value in enumerate(input_list) if value.shape[0])
        stage_seconds["expert_dispatch"] += time.perf_counter() - started

        weights, event = store.activate_cpu(required, layer_input.dtype)
        stage_seconds["storage_and_decode"] += event["storage_and_decode_seconds"]
        stage_seconds["cache_lookup_and_materialisation"] += (
            event["total_seconds"] - event["storage_and_decode_seconds"]
        )
        observer.observe()

        started = time.perf_counter()
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
    parser.add_argument("--route-corpus", type=Path, required=True)
    parser.add_argument("--memory-budget-gib", type=float, default=3.0)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--device", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--dtype", choices=("float16", "bfloat16"), default="bfloat16")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.storage_root.resolve()
    _verify_storage_device(root, args.device)
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

    shards = json.loads(paths["shards"].read_text(encoding="utf-8"))
    packs = json.loads(paths["packs"].read_text(encoding="utf-8"))
    if not all(shards["integrity"].values()) or not all(packs["integrity"].values()):
        raise RuntimeError("manifest integrity gate failed")
    if packs["source_manifest_sha256"] != _sha256(paths["shards"]):
        raise RuntimeError("pack/source manifest binding failed")
    stored_expert_precision = packs.get("target_dtype", packs.get("source_dtype", "bfloat16"))
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
        raise RuntimeError("CPU feasibility prompt did not reach model fallback")

    model_dtype = torch.float16 if args.dtype == "float16" else torch.bfloat16
    memory = [_cpu_memory("before_model_load")]
    load_started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(paths["model"], local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        paths["model"], local_files_only=True, dtype=model_dtype,
        device_map={"": "cpu"}, low_cpu_mem_usage=True,
    ).eval()
    checkpoint_load_seconds = time.perf_counter() - load_started
    memory.append(_cpu_memory("full_cpu_model_loaded"))

    def generate() -> dict[str, Any]:
        inputs = tokenizer.apply_chat_template(
            [{"role": "user", "content": routed.fallback_prompt}],
            add_generation_prompt=True,
            tokenize=True,
            return_tensors="pt",
            return_dict=True,
        )
        started = time.perf_counter()
        with torch.inference_mode():
            generated = model.generate(
                **inputs, do_sample=False, max_new_tokens=1, use_cache=True,
                return_dict_in_generate=True, output_scores=True,
                pad_token_id=tokenizer.eos_token_id,
            )
        continuation = generated.sequences[0, inputs["input_ids"].shape[1]:].detach()
        return {
            "token_ids": continuation.tolist(),
            "text": tokenizer.decode(continuation),
            "score": generated.scores[0][0].detach().float().clone(),
            "seconds": time.perf_counter() - started,
        }

    control = generate()
    memory.append(_cpu_memory("after_full_cpu_control"))
    layers = list(model.model.layers)
    stores = []
    for number, (layer, index, pack_layer) in enumerate(
        zip(layers, indexes, packs["layers"], strict=True)
    ):
        store = CpuPackedLayerStore(number, index, pack_layer)
        store.preverify(root)
        stores.append(store)
        layer.block_sparse_moe.input_linear = None
        layer.block_sparse_moe.output_linear = None
    gc.collect()
    memory.append(_cpu_memory("experts_removed"))

    stages = {
        "router_and_route_capture": 0.0,
        "expert_dispatch": 0.0,
        "storage_and_decode": 0.0,
        "cache_lookup_and_materialisation": 0.0,
        "expert_compute_and_combine": 0.0,
        "cache_policy_and_eviction": 0.0,
    }
    observer = CpuObserver()
    for layer, store, capacity in zip(layers, stores, capacities, strict=True):
        layer.block_sparse_moe.forward = _cpu_streamed_forward(
            layer.block_sparse_moe, store, observer, capacity, stages
        )
    disk_before = _disk_snapshot(args.device)
    streamed = generate()
    disk_after = _disk_snapshot(args.device)
    errors = (streamed["score"] - control["score"]).abs()
    activations = [
        event for store in stores for event in store.events
        if event["kind"] == "cpu_layer_activation"
    ]
    integrity = {
        "token_ids_exact_match": streamed["token_ids"] == control["token_ids"],
        "all_logits_exact_match": float(errors.max().item()) == 0.0,
        "all_32_layer_packs_verified": len(stores) == 32,
        "all_1280_experts_addressable": sum(len(store.verified) for store in stores) == 1280,
        "controller_memory_within_declared_ceiling": (
            memory_plan.estimated_resident_bytes <= memory_plan.maximum_resident_bytes
        ),
        "all_artifacts_on_external_storage": all(
            root in path.parents for path in (*paths.values(), output)
        ),
    }
    control.pop("score")
    streamed.pop("score")
    report = {
        "schema_version": "aion.cpu_streaming_feasibility.v1",
        "run_id": args.run_id,
        "storage_root": str(root),
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": {name: _sha256(path) for name, path in paths.items() if path.is_file()},
        "method": {
            "prompt_count": 1,
            "generated_tokens": 1,
            "full_cpu_control": True,
            "streamed_cpu_experts": True,
            "expert_precision": args.dtype,
            "stored_expert_precision": stored_expert_precision,
            "dtype_conversion_required": args.dtype != stored_expert_precision,
            "same_model_load": True,
            "cache_condition": "warm_uncontrolled",
            "promotion_run": False,
        },
        "capacity_source": {
            "maximum_resident_bytes": memory_plan.maximum_resident_bytes,
            "estimated_resident_bytes": memory_plan.estimated_resident_bytes,
            "capacities_by_layer": capacities,
            "plan_sha256": memory_plan.plan_sha256,
        },
        "gateway": {
            "glyph_address": routed.glyph_address,
            "model_input_sha256": hashlib.sha256(routed.fallback_prompt.encode()).hexdigest(),
            "proof_receipt_sha256": routed.proof_receipt["proof_receipt_sha256"],
        },
        "control": control,
        "streamed": {
            **streamed,
            "maximum_logit_error": float(errors.max().item()),
            "demand_faults": sum(event["demand_faults"] for event in activations),
            "demand_logical_bytes": sum(event["demand_logical_bytes"] for event in activations),
            "retained_hits": sum(event["retained_hits"] for event in activations),
            "peak_rss_bytes": observer.peak_rss_bytes,
        },
        "stages": stages,
        "physical_disk_observation": {
            "device": args.device,
            "read_bytes_delta": disk_after["read_bytes"] - disk_before["read_bytes"],
            "read_count_delta": disk_after["read_count"] - disk_before["read_count"],
            "system_wide_counter": True,
            "exclusive_process_attribution": False,
        },
        "timing": {"checkpoint_load_seconds": checkpoint_load_seconds},
        "memory": memory,
        "integrity": integrity,
        "feasibility_passed": all(integrity.values()),
        "claim_boundary": (
            "One prompt and one generated token establish only CPU-streaming feasibility and "
            "same-backend exactness. This is not a throughput or promotion result. File-cache "
            "state is warm uncontrolled and disk counters are system-wide."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "report_sha256": report["report_sha256"],
        "control": control,
        "streamed": report["streamed"],
        "stages": stages,
        "memory": memory,
        "integrity": integrity,
    }, indent=2))
    return 0 if all(integrity.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
