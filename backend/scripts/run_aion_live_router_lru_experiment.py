#!/usr/bin/env python3
"""Compare one-route and two-route live MoE retention on longer generation."""

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

from backend.modules.aion_inference import AdaptiveInferenceRuntime
from backend.scripts.run_aion_layer_scoped_moe_experiment import (
    LayerAheadCoordinator,
    LayerScopedStore,
    _chat_tokens,
    _layer_scoped_forward,
)
from backend.scripts.run_aion_moe_end_to_end_fault_in import _memory_snapshot, _sha256


CASES = (
    {
        "prompt": "Explain how a 7 percent tax changes a quoted price without calculating it.",
        "generated_tokens": 8,
    },
    {
        "prompt": "Human review is required and payment is forbidden. What can happen next?",
        "generated_tokens": 16,
    },
)
CONDITIONS = ("request_scoped_control", "live_router_depth_1", "live_router_depth_2_lru")


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--shard-manifest", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.storage_root.resolve()
    model_path, profile_path, manifest_path = (
        args.model_path.resolve(), args.profile.resolve(), args.shard_manifest.resolve()
    )
    if any(root not in path.parents for path in (model_path, profile_path, manifest_path)):
        raise SystemExit("model, profile, shards and evidence must reside on external storage")
    if not torch.backends.mps.is_available():
        raise SystemExit("Apple Metal/MPS is required")
    output = args.output or root / "experiments" / f"{args.run_id}.json"
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    experts_per_token = int(profile["architecture"]["experts_selected_per_token"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not all(manifest["integrity"].values()):
        raise RuntimeError("shard manifest integrity gate failed")

    evidence_root = root / "runtime-evidence" / args.run_id
    runtime = AdaptiveInferenceRuntime(
        replay_path=evidence_root / "replay.sqlite3",
        trace_path=evidence_root / "trace.jsonl",
    )
    requests = []
    for case in CASES:
        routed = runtime.route(case["prompt"])
        if not routed.model_call_required or not routed.fallback_prompt:
            raise RuntimeError("long-generation case did not reach the model fallback")
        requests.append({
            **case,
            "glyph_address": routed.glyph_address,
            "model_input": routed.fallback_prompt,
            "model_input_sha256": hashlib.sha256(routed.fallback_prompt.encode("utf-8")).hexdigest(),
            "gateway_prediction": dict(routed.proof_receipt["model_route_prediction"]),
            "gateway_proof_receipt_sha256": routed.proof_receipt["proof_receipt_sha256"],
        })

    checkpoint_started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        local_files_only=True,
        dtype=torch.float16,
        device_map={"": "mps"},
        low_cpu_mem_usage=True,
    ).eval()
    checkpoint_load_seconds = time.perf_counter() - checkpoint_started

    def generate(prompt: str, generated_tokens: int) -> dict[str, Any]:
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
            "score_tensors": [score[0].detach().float().cpu() for score in generated.scores],
            "seconds": time.perf_counter() - started,
        }

    unrestricted = [
        generate(request["model_input"], request["generated_tokens"]) for request in requests
    ]
    unrestricted_memory = _memory_snapshot("after_unrestricted")

    layers = list(model.model.layers)
    if len(layers) != len(manifest["layers"]):
        raise RuntimeError("model and shard-manifest layer counts differ")
    stores: list[LayerScopedStore] = []
    for layer_number, (layer, manifest_layer) in enumerate(zip(layers, manifest["layers"], strict=True)):
        index_path = Path(manifest_layer["index_path"])
        if root not in index_path.resolve().parents or _sha256(index_path) != manifest_layer["index_sha256"]:
            raise RuntimeError(f"layer index integrity failed: {layer_number}")
        store = LayerScopedStore(layer_number, json.loads(index_path.read_text(encoding="utf-8")))
        stores.append(store)
        layer.block_sparse_moe.input_linear = None
        layer.block_sparse_moe.output_linear = None
    gc.collect()
    torch.mps.empty_cache()
    stripped_memory = _memory_snapshot("expert_tensors_removed")

    verification_started = time.perf_counter()
    for store in stores:
        store.preverify(root)
    verification_seconds = time.perf_counter() - verification_started

    trials = []
    empty_plan = tuple(() for _ in stores)
    for request_number, (request, control) in enumerate(zip(requests, unrestricted, strict=True)):
        for condition in CONDITIONS:
            for store in stores:
                store.clear_all()
            gc.collect()
            torch.mps.empty_cache()
            event_starts = [len(store.events) for store in stores]
            coordinator = LayerAheadCoordinator(stores, empty_plan)
            retention_depth = 1 if condition == "live_router_depth_1" else 2 if condition == "live_router_depth_2_lru" else 0
            for layer, store in zip(layers, stores, strict=True):
                layer.block_sparse_moe.forward = _layer_scoped_forward(
                    layer.block_sparse_moe,
                    store,
                    coordinator,
                    retention_depth=retention_depth,
                    retain_request_scope=condition == "request_scoped_control",
                )
            result = generate(request["model_input"], request["generated_tokens"])
            coordinator.close()
            events = [
                event
                for store, start in zip(stores, event_starts, strict=True)
                for event in store.events[start:]
            ]
            activations = [event for event in events if event["kind"] == "layer_activation"]
            score_errors = [
                float((observed - expected).abs().max().item())
                for observed, expected in zip(
                    result["score_tensors"], control["score_tensors"], strict=True
                )
            ]
            retained_experts = sum(len(store.retained) for store in stores)
            retained_bytes = sum(
                store.entries[expert]["bytes"] for store in stores for expert in store.retained
            )
            decode_expert_activations = (
                max(0, len(result["token_ids"]) - 1) * len(stores) * experts_per_token
            )
            retained_hits = sum(event["retained_hits"] for event in activations)
            trials.append({
                "request_number": request_number,
                "public_prompt": request["prompt"],
                "generated_tokens_requested": request["generated_tokens"],
                "generated_tokens_observed": len(result["token_ids"]),
                "condition": condition,
                "retention_depth": retention_depth,
                "seconds": result["seconds"],
                "peak_mps_bytes": coordinator.peak_mps_bytes,
                "peak_rss_bytes": coordinator.peak_rss_bytes,
                "retained_experts_after_generation": retained_experts,
                "retained_logical_bytes_after_generation": retained_bytes,
                "required_expert_activations": sum(event["required_experts"] for event in activations),
                "decode_expert_activations": decode_expert_activations,
                "retained_hits": retained_hits,
                "decode_retained_hit_rate": (
                    retained_hits / decode_expert_activations if decode_expert_activations else 0.0
                ),
                "demand_faults": sum(event["demand_faults"] for event in activations),
                "demand_logical_bytes": sum(event["demand_logical_bytes"] for event in activations),
                "token_ids": result["token_ids"],
                "text": result["text"],
                "token_ids_exact_match": result["token_ids"] == control["token_ids"],
                "all_step_logits_exact_match": all(error == 0.0 for error in score_errors),
                "maximum_step_logit_error": max(score_errors, default=0.0),
            })
            for store in stores:
                store.clear_all()
            gc.collect()
            torch.mps.empty_cache()

    for control in unrestricted:
        control.pop("score_tensors")
    aggregates = {}
    for condition in CONDITIONS:
        group = [trial for trial in trials if trial["condition"] == condition]
        aggregates[condition] = {
            "median_seconds": statistics.median(trial["seconds"] for trial in group),
            "maximum_peak_mps_bytes": max(trial["peak_mps_bytes"] for trial in group),
            "maximum_retained_experts": max(trial["retained_experts_after_generation"] for trial in group),
            "total_required_expert_activations": sum(trial["required_expert_activations"] for trial in group),
            "total_retained_hits": sum(trial["retained_hits"] for trial in group),
            "retained_hit_rate": (
                sum(trial["retained_hits"] for trial in group)
                / sum(trial["required_expert_activations"] for trial in group)
            ),
            "decode_retained_hit_rate": (
                sum(trial["retained_hits"] for trial in group)
                / sum(trial["decode_expert_activations"] for trial in group)
            ),
            "total_demand_faults": sum(trial["demand_faults"] for trial in group),
            "total_demand_logical_bytes": sum(trial["demand_logical_bytes"] for trial in group),
            "all_outputs_exact": all(
                trial["token_ids_exact_match"] and trial["all_step_logits_exact_match"]
                for trial in group
            ),
        }

    request_scope = aggregates["request_scoped_control"]
    depth_1 = aggregates["live_router_depth_1"]
    depth_2 = aggregates["live_router_depth_2_lru"]
    outcomes = {
        "depth_2_time_change_percent_vs_depth_1": 100.0 * (
            depth_2["median_seconds"] / depth_1["median_seconds"] - 1.0
        ),
        "depth_2_logical_byte_change_percent_vs_depth_1": 100.0 * (
            depth_2["total_demand_logical_bytes"] / depth_1["total_demand_logical_bytes"] - 1.0
        ),
        "depth_2_peak_mps_change_percent_vs_depth_1": 100.0 * (
            depth_2["maximum_peak_mps_bytes"] / depth_1["maximum_peak_mps_bytes"] - 1.0
        ),
        "depth_2_peak_mps_reduction_percent_vs_request_scope": 100.0 * (
            1.0 - depth_2["maximum_peak_mps_bytes"] / request_scope["maximum_peak_mps_bytes"]
        ),
        "depth_2_time_change_percent_vs_request_scope": 100.0 * (
            depth_2["median_seconds"] / request_scope["median_seconds"] - 1.0
        ),
        "depth_2_improves_time_by_at_least_5_percent_vs_depth_1": (
            depth_2["median_seconds"] <= depth_1["median_seconds"] * 0.95
        ),
        "depth_2_uses_at_most_half_request_scope_peak_mps": (
            depth_2["maximum_peak_mps_bytes"] <= request_scope["maximum_peak_mps_bytes"] * 0.5
        ),
    }
    integrity = {
        "all_32_layers_dynamic": len(stores) == 32,
        "all_1280_shards_preverified": sum(len(store.verified) for store in stores) == 1280,
        "eight_and_sixteen_token_cases_completed": {
            trial["generated_tokens_observed"] for trial in trials
        } == {8, 16},
        "depth_2_cache_bounded_to_512_experts": (
            depth_2["maximum_retained_experts"] <= len(stores) * 16
        ),
        "all_token_ids_and_step_logits_exact": all(
            trial["token_ids_exact_match"] and trial["all_step_logits_exact_match"]
            for trial in trials
        ),
        "model_profile_shards_and_evidence_on_external_storage": all(
            root in path.resolve().parents for path in (model_path, profile_path, manifest_path, output)
        ),
    }
    report = {
        "schema_version": "aion.live_router_lru_experiment.v1",
        "run_id": args.run_id,
        "storage_root": str(root),
        "model_path": str(model_path),
        "profile_path": str(profile_path),
        "profile_sha256": _sha256(profile_path),
        "shard_manifest_path": str(manifest_path),
        "shard_manifest_sha256": _sha256(manifest_path),
        "gateway_trace_path": str(evidence_root / "trace.jsonl"),
        "gateway_trace_sha256": _sha256(evidence_root / "trace.jsonl"),
        "method": {
            "cases": CASES,
            "conditions": CONDITIONS,
            "retention_unit": "most_recent_live_token_routes_per_layer",
            "request_scope_control_in_same_run": True,
            "immediate_nonretained_layer_eviction": True,
            "os_file_cache_controlled": False,
        },
        "requests": requests,
        "unrestricted": unrestricted,
        "trials": trials,
        "aggregates": aggregates,
        "outcomes": outcomes,
        "timing": {
            "checkpoint_load_seconds": checkpoint_load_seconds,
            "shard_preverification_seconds": verification_seconds,
        },
        "memory": {
            "unrestricted": unrestricted_memory,
            "experts_removed": stripped_memory,
        },
        "integrity": integrity,
        "claim_boundary": (
            "This is a same-run, two-prompt comparison of request-wide, one-route and two-route "
            "live expert retention for exact 8-token and 16-token Granite generation from SD-backed "
            "shards. It does not establish population-level latency, cold physical SD reads, energy "
            "saving, or transfer to other prompts, output lengths, models or storage media."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "report_sha256": report["report_sha256"],
        "aggregates": aggregates,
        "outcomes": outcomes,
        "integrity": integrity,
    }, indent=2))
    return 0 if all(integrity.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
