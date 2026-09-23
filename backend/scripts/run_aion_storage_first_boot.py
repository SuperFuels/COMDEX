#!/usr/bin/env python3
"""Construct Granite MoE without first materializing checkpoint experts."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import time
from typing import Any

from accelerate import init_empty_weights
from accelerate.utils import set_module_tensor_to_device
import psutil
from safetensors import safe_open
import torch
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer

from backend.modules.aion_inference import AdaptiveInferenceRuntime, ExpertRouteCorpus
from backend.scripts.run_aion_layer_pack_experiment import PackedLayerScopedStore
from backend.scripts.run_aion_layer_scoped_moe_experiment import (
    LayerAheadCoordinator,
    _chat_tokens,
    _layer_scoped_forward,
)
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256


DEFAULT_PROMPT = "Human review is required and payment is forbidden. What can happen next?"
EXPERT_SUFFIXES = (
    ".block_sparse_moe.input_linear.weight",
    ".block_sparse_moe.output_linear.weight",
)


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _is_expert_tensor(name: str) -> bool:
    return name.endswith(EXPERT_SUFFIXES)


def _memory(label: str) -> dict[str, int | str]:
    return {
        "label": label,
        "mps_current_allocated_bytes": torch.mps.current_allocated_memory(),
        "mps_driver_allocated_bytes": torch.mps.driver_allocated_memory(),
        "process_rss_bytes": psutil.Process().memory_info().rss,
        "system_available_bytes": psutil.virtual_memory().available,
    }


def _generate(model, tokenizer, prompt: str, generated_tokens: int) -> dict[str, Any]:
    inputs = _chat_tokens(tokenizer, prompt)
    started = time.perf_counter()
    with torch.inference_mode():
        generated = model.generate(
            **inputs,
            do_sample=False,
            max_new_tokens=generated_tokens,
            use_cache=True,
            return_dict_in_generate=True,
            output_scores=True,
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


def _verify_source_checkpoint(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    results = []
    for entry in manifest["source_checkpoint"]:
        path = Path(entry["path"]).resolve()
        passed = (
            root in path.parents
            and path.is_file()
            and path.stat().st_size == int(entry["bytes"])
            and _sha256(path) == entry["sha256"]
        )
        results.append({"path": str(path), "sha256": entry["sha256"], "passed": passed})
    return {
        "seconds": time.perf_counter() - started,
        "objects": results,
        "passed": all(item["passed"] for item in results),
    }


def _load_storage_first_model(
    model_path: Path,
    index: dict[str, Any],
) -> tuple[Any, dict[str, Any]]:
    config = AutoConfig.from_pretrained(model_path, local_files_only=True)
    started = time.perf_counter()
    # Parameters must remain unallocated until their verified object is loaded.
    # Small deterministic buffers (notably RoPE inv_freq) must be initialized
    # normally because they are not checkpoint tensors.
    with init_empty_weights(include_buffers=False):
        model = AutoModelForCausalLM.from_config(config, dtype=torch.float16)
    construction_seconds = time.perf_counter() - started

    weight_map = index["weight_map"]
    expert_names = {name for name in weight_map if _is_expert_tensor(name)}
    shared_names = set(weight_map).difference(expert_names)
    peak_mps = torch.mps.current_allocated_memory()
    load_started = time.perf_counter()
    for shard_name in sorted(set(weight_map.values())):
        names = sorted(name for name, mapped in weight_map.items() if mapped == shard_name)
        with safe_open(model_path / shard_name, framework="pt", device="cpu") as handle:
            for name in names:
                if name in expert_names:
                    continue
                set_module_tensor_to_device(
                    model,
                    name,
                    "mps",
                    value=handle.get_tensor(name),
                    dtype=torch.float16,
                )
                peak_mps = max(peak_mps, torch.mps.current_allocated_memory())

    for layer in model.model.layers:
        layer.block_sparse_moe.input_linear = None
        layer.block_sparse_moe.output_linear = None
    model.tie_weights()
    remaining_meta = sorted(name for name, value in model.named_parameters() if value.is_meta)
    remaining_meta_buffers = sorted(name for name, value in model.named_buffers() if value.is_meta)
    model.eval()
    torch.mps.synchronize()
    return model, {
        "skeleton_construction_seconds": construction_seconds,
        "shared_tensor_load_seconds": time.perf_counter() - load_started,
        "checkpoint_tensor_count": len(weight_map),
        "shared_tensor_count": len(shared_names),
        "skipped_expert_tensor_count": len(expert_names),
        "skipped_expert_names_sha256": _canonical_sha256(sorted(expert_names)),
        "peak_mps_allocated_bytes": peak_mps,
        "remaining_meta_parameters": remaining_meta,
        "remaining_meta_buffers": remaining_meta_buffers,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--shard-manifest", type=Path, required=True)
    parser.add_argument("--pack-manifest", type=Path, required=True)
    parser.add_argument("--route-corpus", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--memory-budget-gib", type=float, default=3.0)
    parser.add_argument("--generated-tokens", type=int, default=1)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if not torch.backends.mps.is_available():
        raise SystemExit("Apple Metal/MPS is required")
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

    shards = json.loads(paths["shards"].read_text(encoding="utf-8"))
    packs = json.loads(paths["packs"].read_text(encoding="utf-8"))
    checkpoint_index_path = paths["model"] / "model.safetensors.index.json"
    checkpoint_index = json.loads(checkpoint_index_path.read_text(encoding="utf-8"))
    if not all(shards["integrity"].values()) or not all(packs["integrity"].values()):
        raise RuntimeError("manifest integrity gate failed")
    if packs["source_manifest_sha256"] != _sha256(paths["shards"]):
        raise RuntimeError("pack/source manifest binding failed")

    source_verification = _verify_source_checkpoint(root, shards)
    if not source_verification["passed"]:
        raise RuntimeError("source checkpoint verification failed closed")

    indexes = []
    entries_by_layer = []
    for number, shard_layer in enumerate(shards["layers"]):
        index_path = Path(shard_layer["index_path"])
        if root not in index_path.resolve().parents or _sha256(index_path) != shard_layer["index_sha256"]:
            raise RuntimeError(f"expert index verification failed: layer {number}")
        layer_index = json.loads(index_path.read_text(encoding="utf-8"))
        indexes.append(layer_index)
        entries_by_layer.append({int(entry["expert"]): entry for entry in layer_index["experts"]})

    stores = []
    pack_verify_started = time.perf_counter()
    for number, (layer_index, pack_layer) in enumerate(zip(indexes, packs["layers"], strict=True)):
        store = PackedLayerScopedStore(number, layer_index, pack_layer)
        store.preverify(root)
        stores.append(store)
    pack_verification_seconds = time.perf_counter() - pack_verify_started

    corpus = ExpertRouteCorpus(paths["route_corpus"])
    observations = tuple(sorted(path.stem for path in corpus.objects.glob("*.json")))
    memory_plan = corpus.optimize_memory(
        observations,
        entries_by_layer,
        maximum_resident_bytes=int(args.memory_budget_gib * 1024**3),
    )
    runtime_root = root / "runtime-evidence" / args.run_id
    routed = AdaptiveInferenceRuntime(
        replay_path=runtime_root / "replay.sqlite3",
        trace_path=runtime_root / "trace.jsonl",
    ).route(args.prompt)
    if not routed.model_call_required or not routed.fallback_prompt:
        raise RuntimeError("prompt did not reach model fallback")

    tokenizer = AutoTokenizer.from_pretrained(paths["model"], local_files_only=True)
    memory = [_memory("before_full_control_load")]
    full_started = time.perf_counter()
    full_model = AutoModelForCausalLM.from_pretrained(
        paths["model"], local_files_only=True, dtype=torch.float16,
        device_map={"": "mps"}, low_cpu_mem_usage=True,
    ).eval()
    torch.mps.synchronize()
    full_load_seconds = time.perf_counter() - full_started
    full_startup = _memory("after_full_control_load")
    memory.append(full_startup)
    control_first = _generate(full_model, tokenizer, routed.fallback_prompt, args.generated_tokens)
    control_second = _generate(full_model, tokenizer, routed.fallback_prompt, args.generated_tokens)
    del full_model
    gc.collect()
    torch.mps.empty_cache()
    memory.append(_memory("after_full_control_release"))

    storage_model, storage_boot = _load_storage_first_model(paths["model"], checkpoint_index)
    memory.append(_memory("after_storage_first_shared_load"))
    coordinator = LayerAheadCoordinator(stores, tuple(() for _ in stores))
    for layer, store, capacity in zip(
        storage_model.model.layers, stores, memory_plan.capacities_by_layer, strict=True
    ):
        layer.block_sparse_moe.forward = _layer_scoped_forward(
            layer.block_sparse_moe,
            store,
            coordinator,
            retention_capacity=capacity,
        )
    storage_first = _generate(
        storage_model, tokenizer, routed.fallback_prompt, args.generated_tokens
    )
    storage_second = _generate(
        storage_model, tokenizer, routed.fallback_prompt, args.generated_tokens
    )
    coordinator.close()

    first_errors = [
        float((actual - expected).abs().max().item())
        for actual, expected in zip(storage_first["scores"], control_first["scores"], strict=True)
    ]
    second_errors = [
        float((actual - expected).abs().max().item())
        for actual, expected in zip(storage_second["scores"], control_second["scores"], strict=True)
    ]
    activations = [event for store in stores for event in store.events if event["kind"] == "layer_activation"]
    integrity = {
        "source_checkpoint_hashes_verified": source_verification["passed"],
        "pack_manifest_bound_to_shards": packs["source_manifest_sha256"] == _sha256(paths["shards"]),
        "all_32_layer_packs_verified": len(stores) == 32,
        "all_1280_experts_addressable": sum(len(store.verified) for store in stores) == 1280,
        "exactly_64_checkpoint_expert_tensors_skipped": storage_boot["skipped_expert_tensor_count"] == 64,
        "no_meta_parameters_reach_execution": not storage_boot["remaining_meta_parameters"],
        "no_meta_buffers_reach_execution": not storage_boot["remaining_meta_buffers"],
        "first_token_ids_exact": storage_first["token_ids"] == control_first["token_ids"],
        "first_step_logits_exact": all(error == 0.0 for error in first_errors),
        "subsequent_token_ids_exact": storage_second["token_ids"] == control_second["token_ids"],
        "subsequent_step_logits_exact": all(error == 0.0 for error in second_errors),
        "controller_memory_within_declared_ceiling": memory_plan.estimated_resident_bytes <= memory_plan.maximum_resident_bytes,
    }
    for result in (control_first, control_second, storage_first, storage_second):
        result.pop("scores")
    report = {
        "schema_version": "aion.storage_first_boot.v1",
        "run_id": args.run_id,
        "storage_root": str(root),
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": {
            "shard_manifest": _sha256(paths["shards"]),
            "pack_manifest": _sha256(paths["packs"]),
            "checkpoint_index": _sha256(checkpoint_index_path),
        },
        "method": {
            "generated_tokens_per_inference": args.generated_tokens,
            "inference_count_per_condition": 2,
            "dtype": "float16",
            "device": "mps",
            "warm_cache_uncontrolled": True,
            "promotion_run": False,
        },
        "verification": {
            "source_checkpoint": source_verification,
            "pack_verification_seconds": pack_verification_seconds,
        },
        "full_checkpoint_control": {
            "load_seconds": full_load_seconds,
            "startup_memory": full_startup,
            "first": control_first,
            "second": control_second,
        },
        "storage_first": {
            "boot": storage_boot,
            "first": {
                **storage_first,
                "maximum_logit_error": max(first_errors, default=0.0),
            },
            "second": {
                **storage_second,
                "maximum_logit_error": max(second_errors, default=0.0),
            },
            "demand_faults": sum(int(event["demand_faults"]) for event in activations),
            "demand_logical_bytes": sum(int(event["demand_logical_bytes"]) for event in activations),
            "retained_hits": sum(int(event["retained_hits"]) for event in activations),
            "peak_mps_during_generation_bytes": coordinator.peak_mps_bytes,
            "peak_rss_during_generation_bytes": coordinator.peak_rss_bytes,
        },
        "memory": memory,
        "capacity": {
            "maximum_resident_bytes": memory_plan.maximum_resident_bytes,
            "estimated_resident_bytes": memory_plan.estimated_resident_bytes,
            "plan_sha256": memory_plan.plan_sha256,
        },
        "integrity": integrity,
        "feasibility_passed": all(integrity.values()),
        "claim_boundary": (
            "This bounded warm-uncontrolled two-inference probe tests storage-first construction, "
            "startup memory and exactness. It is not a cold-start or throughput promotion result."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "report_sha256": report["report_sha256"],
        "full_checkpoint_control": report["full_checkpoint_control"],
        "storage_first": report["storage_first"],
        "integrity": integrity,
    }, indent=2))
    return 0 if all(integrity.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
