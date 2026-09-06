#!/usr/bin/env python3
"""Measure the latency/memory frontier of packed live-route LRU depths."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import time
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from backend.modules.aion_inference import AdaptiveInferenceRuntime
from backend.scripts.run_aion_layer_pack_experiment import PackedLayerScopedStore
from backend.scripts.run_aion_layer_scoped_moe_experiment import (
    LayerAheadCoordinator,
    _chat_tokens,
    _layer_scoped_forward,
)
from backend.scripts.run_aion_moe_end_to_end_fault_in import _memory_snapshot, _sha256


PROMPT = "Human review is required and payment is forbidden. What can happen next?"
DEPTHS = (2, 4, 8)


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--shard-manifest", type=Path, required=True)
    parser.add_argument("--pack-manifest", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--generated-tokens", type=int, default=16)
    parser.add_argument(
        "--frequency-capacities",
        help="comma-separated LFU capacities; compares depth 8 with these capacities",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.storage_root.resolve()
    paths = {
        "model": args.model_path.resolve(),
        "profile": args.profile.resolve(),
        "shards": args.shard_manifest.resolve(),
        "packs": args.pack_manifest.resolve(),
    }
    output = (args.output or root / "experiments" / f"{args.run_id}.json").resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all artifacts must reside on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    if not torch.backends.mps.is_available():
        raise SystemExit("Apple Metal/MPS is required")

    shards = json.loads(paths["shards"].read_text(encoding="utf-8"))
    packs = json.loads(paths["packs"].read_text(encoding="utf-8"))
    if not all(shards["integrity"].values()) or not all(packs["integrity"].values()):
        raise RuntimeError("manifest integrity gate failed")
    if packs["source_manifest_sha256"] != _sha256(paths["shards"]):
        raise RuntimeError("pack/source binding failed")

    evidence_root = root / "runtime-evidence" / args.run_id
    runtime = AdaptiveInferenceRuntime(
        replay_path=evidence_root / "replay.sqlite3",
        trace_path=evidence_root / "trace.jsonl",
    )
    routed = runtime.route(PROMPT)
    if not routed.model_call_required or not routed.fallback_prompt:
        raise RuntimeError("prompt did not reach model fallback")

    started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(paths["model"], local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        paths["model"], local_files_only=True, dtype=torch.float16,
        device_map={"": "mps"}, low_cpu_mem_usage=True,
    ).eval()
    checkpoint_load_seconds = time.perf_counter() - started

    def generate() -> dict[str, Any]:
        inputs = _chat_tokens(tokenizer, routed.fallback_prompt)
        began = time.perf_counter()
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
            "seconds": time.perf_counter() - began,
        }

    control = generate()
    unrestricted_memory = _memory_snapshot("after_unrestricted")
    layers = list(model.model.layers)
    stores = []
    for number, (layer, shard_layer, pack_layer) in enumerate(
        zip(layers, shards["layers"], packs["layers"], strict=True)
    ):
        index_path = Path(shard_layer["index_path"])
        if _sha256(index_path) != shard_layer["index_sha256"]:
            raise RuntimeError(f"index integrity failed: layer {number}")
        store = PackedLayerScopedStore(
            number, json.loads(index_path.read_text(encoding="utf-8")), pack_layer
        )
        store.preverify(root)
        stores.append(store)
        layer.block_sparse_moe.input_linear = None
        layer.block_sparse_moe.output_linear = None
    gc.collect()
    torch.mps.empty_cache()
    stripped_memory = _memory_snapshot("expert_tensors_removed")

    policies = [("route_lru", depth) for depth in DEPTHS]
    if args.frequency_capacities:
        capacities = tuple(int(value) for value in args.frequency_capacities.split(","))
        if not capacities or any(value < 1 or value > 40 for value in capacities):
            raise SystemExit("frequency capacities must be between 1 and 40")
        policies = [("route_lru", 8), *(("frequency_lfu", value) for value in capacities)]
    trials = []
    empty_plan = tuple(() for _ in stores)
    for policy, value in policies:
        for store in stores:
            store.clear_all()
        gc.collect()
        torch.mps.empty_cache()
        event_starts = [len(store.events) for store in stores]
        open_start = sum(store.pack_opens for store in stores)
        coordinator = LayerAheadCoordinator(stores, empty_plan)
        for layer, store in zip(layers, stores, strict=True):
            layer.block_sparse_moe.forward = _layer_scoped_forward(
                layer.block_sparse_moe,
                store,
                coordinator,
                retention_depth=value if policy == "route_lru" else 0,
                retention_capacity=value if policy == "frequency_lfu" else 0,
            )
        result = generate()
        coordinator.close()
        events = [
            event for store, start_at in zip(stores, event_starts, strict=True)
            for event in store.events[start_at:] if event["kind"] == "layer_activation"
        ]
        errors = [
            float((observed - expected).abs().max().item())
            for observed, expected in zip(result["scores"], control["scores"], strict=True)
        ]
        retained_experts = sum(len(store.retained) for store in stores)
        trials.append({
            "policy": policy,
            "policy_value": value,
            "retention_depth": value if policy == "route_lru" else 0,
            "retention_capacity": value if policy == "frequency_lfu" else 0,
            "seconds": result["seconds"],
            "peak_mps_bytes": coordinator.peak_mps_bytes,
            "peak_rss_bytes": coordinator.peak_rss_bytes,
            "retained_experts_after_generation": retained_experts,
            "retained_logical_bytes_after_generation": sum(
                store.entries[expert]["bytes"] for store in stores for expert in store.retained
            ),
            "retained_hits": sum(event["retained_hits"] for event in events),
            "demand_faults": sum(event["demand_faults"] for event in events),
            "demand_logical_bytes": sum(event["demand_logical_bytes"] for event in events),
            "pack_open_operations": sum(store.pack_opens for store in stores) - open_start,
            "token_ids": result["token_ids"],
            "text": result["text"],
            "token_ids_exact_match": result["token_ids"] == control["token_ids"],
            "all_step_logits_exact_match": all(error == 0.0 for error in errors),
            "maximum_step_logit_error": max(errors, default=0.0),
        })
        for store in stores:
            store.clear_all()

    control.pop("scores")
    baseline = trials[0]
    for trial in trials:
        trial["time_change_percent_vs_baseline"] = 100.0 * (
            trial["seconds"] / baseline["seconds"] - 1.0
        )
        trial["peak_mps_change_percent_vs_baseline"] = 100.0 * (
            trial["peak_mps_bytes"] / baseline["peak_mps_bytes"] - 1.0
        )
        trial["demand_byte_reduction_percent_vs_baseline"] = 100.0 * (
            1.0 - trial["demand_logical_bytes"] / baseline["demand_logical_bytes"]
        )
    integrity = {
        "requested_policies_completed": [
            (trial["policy"], trial["policy_value"]) for trial in trials
        ] == policies,
        "all_32_layer_packs_verified": len(stores) == 32,
        "all_1280_experts_addressable": sum(len(store.verified) for store in stores) == 1280,
        "all_token_ids_and_step_logits_exact": all(
            trial["token_ids_exact_match"] and trial["all_step_logits_exact_match"]
            for trial in trials
        ),
        "all_artifacts_on_external_storage": all(
            root in path.parents for path in (*paths.values(), output)
        ),
    }
    report = {
        "schema_version": "aion.packed_cache_policy_sweep.v1",
        "run_id": args.run_id,
        "storage_root": str(root),
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": {name: _sha256(path) for name, path in paths.items() if path.is_file()},
        "gateway_trace_path": str(evidence_root / "trace.jsonl"),
        "gateway_trace_sha256": _sha256(evidence_root / "trace.jsonl"),
        "method": {
            "prompt": PROMPT, "generated_tokens": args.generated_tokens,
            "policies": policies, "baseline_policy": policies[0], "same_loaded_model": True,
            "packed_layer_storage": True, "os_file_cache_controlled": False,
        },
        "gateway": {
            "glyph_address": routed.glyph_address,
            "proof_receipt_sha256": routed.proof_receipt["proof_receipt_sha256"],
        },
        "control": control,
        "trials": trials,
        "timing": {"checkpoint_load_seconds": checkpoint_load_seconds},
        "memory": {"unrestricted": unrestricted_memory, "experts_removed": stripped_memory},
        "integrity": integrity,
        "claim_boundary": (
            "This single-prompt, ordered depth sweep maps a local latency/memory frontier. It does "
            "not establish population-level performance, cold physical SD reads, or an optimal "
            "depth for other prompts, models, output lengths, or storage media."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output), "report_sha256": report["report_sha256"],
        "trials": trials, "integrity": integrity,
    }, indent=2))
    return 0 if all(integrity.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
