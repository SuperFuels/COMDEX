#!/usr/bin/env python3
"""Connect Gateway expert predictions to real SD-backed Granite MoE prefetch."""

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

from backend.modules.aion_inference import (
    AdaptiveInferenceRuntime,
    broad_expert_prefetch_plan,
    build_expert_prefetch_plan,
)
from backend.scripts.run_aion_moe_end_to_end_fault_in import (
    LayerExpertStore,
    _dynamic_forward,
    _memory_snapshot,
    _sha256,
)


PROMPTS = (
    "Explain how a 7 percent tax changes a quoted price without calculating it.",
    "Human review is required and payment is forbidden. What can happen next?",
    "Explain deterministic replay in software.",
    "Why do leaves change colour?",
)
CONDITIONS = ("no_prefetch", "glyph_targeted_prefetch", "broad_prefetch")


def _chat_tokens(tokenizer, prompt: str) -> dict[str, torch.Tensor]:
    encoded = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}],
        add_generation_prompt=True,
        tokenize=True,
        return_tensors="pt",
        return_dict=True,
    )
    return {key: value.to("mps") for key, value in encoded.items()}


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
    parser.add_argument("--coverage-target", type=float, default=0.90)
    parser.add_argument("--generated-tokens", type=int, default=2)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.storage_root.resolve()
    model_path = args.model_path.resolve()
    profile_path = args.profile.resolve()
    manifest_path = args.shard_manifest.resolve()
    if any(root not in path.parents for path in (model_path, profile_path, manifest_path)):
        raise SystemExit("model, router profile, and shards must all reside under external storage root")
    if not torch.backends.mps.is_available():
        raise SystemExit("Apple Metal/MPS is required")
    output = args.output or root / "experiments" / f"{args.run_id}.json"
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing evidence: {output}")

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not all(manifest["integrity"].values()):
        raise SystemExit("expert shard manifest integrity gate failed")

    evidence_root = root / "runtime-evidence" / args.run_id
    runtime = AdaptiveInferenceRuntime(
        replay_path=evidence_root / "replay.sqlite3",
        trace_path=evidence_root / "trace.jsonl",
    )
    requests = []
    for prompt in PROMPTS:
        routed = runtime.route(prompt)
        if not routed.model_call_required or not routed.fallback_prompt:
            raise RuntimeError(f"experiment prompt did not reach model fallback: {prompt}")
        prediction = dict(routed.proof_receipt["model_route_prediction"])
        plan = build_expert_prefetch_plan(
            profile,
            prediction["expert_prefetch_profile"],
            coverage_target=args.coverage_target,
        )
        requests.append({
            "public_prompt": prompt,
            "glyph_address": routed.glyph_address,
            "model_input": routed.fallback_prompt,
            "model_input_sha256": hashlib.sha256(routed.fallback_prompt.encode("utf-8")).hexdigest(),
            "gateway_prediction": prediction,
            "targeted_plan": plan,
            "proof_receipt_sha256": routed.proof_receipt["proof_receipt_sha256"],
        })

    memory = [_memory_snapshot("before_model_load")]
    load_started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        local_files_only=True,
        dtype=torch.float16,
        device_map={"": "mps"},
        low_cpu_mem_usage=True,
    ).eval()
    checkpoint_load_seconds = time.perf_counter() - load_started
    memory.append(_memory_snapshot("full_model_loaded"))

    def generate(prompt: str) -> dict[str, Any]:
        inputs = _chat_tokens(tokenizer, prompt)
        started = time.perf_counter()
        with torch.inference_mode():
            generated = model.generate(
                **inputs,
                do_sample=False,
                max_new_tokens=args.generated_tokens,
                use_cache=True,
                return_dict_in_generate=True,
                output_scores=True,
                pad_token_id=tokenizer.eos_token_id,
            )
        torch.mps.synchronize()
        continuation = generated.sequences[0, inputs["input_ids"].shape[1]:].detach().cpu()
        logits = generated.scores[0][0].detach().float().cpu()
        return {
            "token_ids": continuation.tolist(),
            "text": tokenizer.decode(continuation),
            "first_token_id": int(logits.argmax()),
            "first_token_logits": logits,
            "generation_seconds": time.perf_counter() - started,
        }

    unrestricted = [generate(item["model_input"]) for item in requests]
    memory.append(_memory_snapshot("after_unrestricted_controls"))

    layers = list(model.model.layers)
    if len(layers) != len(manifest["layers"]):
        raise RuntimeError("model and shard-manifest layer counts differ")
    stores: list[LayerExpertStore] = []
    for layer_number, (layer, manifest_layer) in enumerate(zip(layers, manifest["layers"], strict=True)):
        index_path = Path(manifest_layer["index_path"])
        if root not in index_path.resolve().parents or _sha256(index_path) != manifest_layer["index_sha256"]:
            raise RuntimeError(f"layer index integrity failed: {layer_number}")
        index = json.loads(index_path.read_text(encoding="utf-8"))
        store = LayerExpertStore(layer_number, index, set())
        stores.append(store)
        block = layer.block_sparse_moe
        block.forward = _dynamic_forward(block, store)
        block.input_linear = None
        block.output_linear = None
    gc.collect()
    torch.mps.empty_cache()
    memory.append(_memory_snapshot("expert_tensors_removed"))

    verification_started = time.perf_counter()
    for store in stores:
        for expert, entry in store.entries.items():
            shard = Path(entry["path"])
            if root not in shard.resolve().parents or _sha256(shard) != entry["sha256"]:
                raise RuntimeError(f"expert shard integrity failed: layer {store.layer}, expert {expert}")
            store.verified.add(expert)
    shard_preverification_seconds = time.perf_counter() - verification_started

    broad_plan = broad_expert_prefetch_plan(profile)
    trials: list[dict[str, Any]] = []
    for request_number, (request, control) in enumerate(zip(requests, unrestricted, strict=True)):
        plans = {
            "no_prefetch": tuple(() for _ in stores),
            "glyph_targeted_prefetch": request["targeted_plan"].experts_by_layer,
            "broad_prefetch": broad_plan.experts_by_layer,
        }
        for condition in CONDITIONS:
            for store, residents in zip(stores, plans[condition], strict=True):
                store.clear_all()
                store.configure_resident(set(residents))
            gc.collect()
            torch.mps.empty_cache()
            event_start = [len(store.events) for store in stores]
            total_started = time.perf_counter()
            for store in stores:
                store.phase = f"{condition}:prefetch"
            prefetch_started = time.perf_counter()
            for layer, store in zip(layers, stores, strict=True):
                store.prefetch(layer.input_layernorm.weight.device, layer.input_layernorm.weight.dtype)
            torch.mps.synchronize()
            prefetch_wall_seconds = time.perf_counter() - prefetch_started
            after_prefetch = _memory_snapshot(f"request_{request_number}:{condition}:after_prefetch")
            for store in stores:
                store.phase = f"{condition}:demand"
            result = generate(request["model_input"])
            after_generation = _memory_snapshot(f"request_{request_number}:{condition}:after_generation")
            total_wall_seconds = time.perf_counter() - total_started
            new_events = [
                event
                for store, start in zip(stores, event_start, strict=True)
                for event in store.events[start:]
            ]
            prefetch_events = [event for event in new_events if event["phase"].endswith(":prefetch")]
            demand_events = [event for event in new_events if event["phase"].endswith(":demand")]
            logits = result.pop("first_token_logits")
            control_logits = control["first_token_logits"]
            trials.append({
                "request_number": request_number,
                "public_prompt": request["public_prompt"],
                "glyph_address": request["glyph_address"],
                "predicted_expert_prefetch_profile": request["gateway_prediction"]["expert_prefetch_profile"],
                "condition": condition,
                "plan_sha256": (
                    request["targeted_plan"].plan_sha256 if condition == "glyph_targeted_prefetch"
                    else broad_plan.plan_sha256 if condition == "broad_prefetch" else None
                ),
                "configured_experts": sum(len(layer) for layer in plans[condition]),
                "configured_logical_bytes": sum(
                    store.entries[expert]["bytes"]
                    for store, residents in zip(stores, plans[condition], strict=True)
                    for expert in residents
                ),
                "prefetch_load_events": len(prefetch_events),
                "prefetch_logical_bytes": sum(event["logical_bytes"] for event in prefetch_events),
                "demand_fault_events": len(demand_events),
                "demand_logical_bytes": sum(event["logical_bytes"] for event in demand_events),
                "prefetch_wall_seconds": prefetch_wall_seconds,
                "generation_seconds": result["generation_seconds"],
                "total_wall_seconds": total_wall_seconds,
                "mps_after_prefetch_bytes": after_prefetch["mps_current_allocated_bytes"],
                "mps_after_generation_bytes": after_generation["mps_current_allocated_bytes"],
                "token_ids": result["token_ids"],
                "text": result["text"],
                "token_ids_exact_match": result["token_ids"] == control["token_ids"],
                "first_token_id_match": result["first_token_id"] == control["first_token_id"],
                "first_token_max_absolute_logit_error": float((logits - control_logits).abs().max().item()),
            })
            for store in stores:
                store.clear_all()
            del logits
            gc.collect()
            torch.mps.empty_cache()

    for control in unrestricted:
        control.pop("first_token_logits")
    aggregates = {}
    for condition in CONDITIONS:
        group = [trial for trial in trials if trial["condition"] == condition]
        aggregates[condition] = {
            "median_prefetch_wall_seconds": statistics.median(item["prefetch_wall_seconds"] for item in group),
            "median_generation_seconds": statistics.median(item["generation_seconds"] for item in group),
            "median_total_wall_seconds": statistics.median(item["total_wall_seconds"] for item in group),
            "total_prefetch_logical_bytes": sum(item["prefetch_logical_bytes"] for item in group),
            "total_demand_logical_bytes": sum(item["demand_logical_bytes"] for item in group),
            "total_logical_bytes": sum(
                item["prefetch_logical_bytes"] + item["demand_logical_bytes"] for item in group
            ),
            "all_token_ids_exact_match": all(item["token_ids_exact_match"] for item in group),
        }

    targeted = aggregates["glyph_targeted_prefetch"]
    none = aggregates["no_prefetch"]
    broad = aggregates["broad_prefetch"]
    hypothesis = {
        "targeted_reduces_demand_fault_bytes_vs_no_prefetch": (
            targeted["total_demand_logical_bytes"] < none["total_demand_logical_bytes"]
        ),
        "targeted_uses_fewer_prefetch_bytes_than_broad": (
            targeted["total_prefetch_logical_bytes"] < broad["total_prefetch_logical_bytes"]
        ),
        "targeted_reduces_total_logical_bytes_vs_broad": (
            targeted["total_logical_bytes"] < broad["total_logical_bytes"]
        ),
        "targeted_reduces_median_generation_time_vs_no_prefetch": (
            targeted["median_generation_seconds"] < none["median_generation_seconds"]
        ),
        "targeted_reduces_median_total_time_by_at_least_5_percent_vs_no_prefetch": (
            targeted["median_total_wall_seconds"] <= none["median_total_wall_seconds"] * 0.95
        ),
    }
    effect_sizes = {
        "targeted_generation_time_reduction_percent_vs_no_prefetch": 100.0 * (
            1.0 - targeted["median_generation_seconds"] / none["median_generation_seconds"]
        ),
        "targeted_total_time_reduction_percent_vs_no_prefetch": 100.0 * (
            1.0 - targeted["median_total_wall_seconds"] / none["median_total_wall_seconds"]
        ),
        "targeted_prefetch_byte_reduction_percent_vs_broad": 100.0 * (
            1.0 - targeted["total_prefetch_logical_bytes"] / broad["total_prefetch_logical_bytes"]
        ),
    }
    integrity = {
        "gateway_selected_all_four_profiles": {
            request["gateway_prediction"]["expert_prefetch_profile"] for request in requests
        } == {"arithmetic_business", "policy", "coding", "general"},
        "gateway_prediction_bound_to_every_targeted_plan": all(
            request["gateway_prediction"]["expert_prefetch_profile"] == request["targeted_plan"].profile
            for request in requests
        ),
        "all_32_layers_dynamic": len(stores) == 32,
        "all_1280_shards_preverified": sum(len(store.verified) for store in stores) == 1280,
        "all_conditions_executed": len(trials) == len(PROMPTS) * len(CONDITIONS),
        "all_outputs_match_unrestricted_model": all(item["token_ids_exact_match"] for item in trials),
        "model_profile_shards_and_evidence_on_external_storage": all(
            root in path.resolve().parents
            for path in (model_path, profile_path, manifest_path, output, evidence_root / "trace.jsonl")
        ),
    }
    report = {
        "schema_version": "aion.glyph_moe_prefetch_experiment.v1",
        "run_id": args.run_id,
        "storage_root": str(root),
        "model_path": str(model_path),
        "routing_profile_path": str(profile_path),
        "routing_profile_sha256": _sha256(profile_path),
        "shard_manifest_path": str(manifest_path),
        "shard_manifest_sha256": _sha256(manifest_path),
        "gateway_trace_path": str(evidence_root / "trace.jsonl"),
        "gateway_trace_sha256": _sha256(evidence_root / "trace.jsonl"),
        "method": {
            "prompts": PROMPTS,
            "conditions": CONDITIONS,
            "generated_tokens": args.generated_tokens,
            "targeted_coverage": args.coverage_target,
            "comparison_cache_state": "empty_expert_tensor_cache_before_each_request",
            "shards_preverified_before_timing": True,
            "os_file_cache_controlled": False,
            "model_input": "canonical_minimal_gateway_fallback_prompt",
        },
        "requests": [
            {
                **{key: value for key, value in request.items() if key != "targeted_plan"},
                "targeted_plan": request["targeted_plan"].to_dict(),
            }
            for request in requests
        ],
        "broad_plan": broad_plan.to_dict(),
        "unrestricted_controls": unrestricted,
        "trials": trials,
        "aggregates": aggregates,
        "hypothesis_outcomes": hypothesis,
        "effect_sizes": effect_sizes,
        "timing": {
            "full_checkpoint_load_seconds": checkpoint_load_seconds,
            "all_shard_preverification_seconds": shard_preverification_seconds,
        },
        "memory": {"snapshots": memory},
        "integrity": integrity,
        "claim_boundary": (
            "The Semantic Gateway prediction directly selected real per-layer Granite expert shards "
            "stored on the external SD volume, and exact model outputs were checked. Logical shard "
            "bytes and process timings are measured, but macOS file-cache state and physical SD reads "
            "are not controlled; this is not proof that semantic profiles predict token-level routing."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "report_sha256": report["report_sha256"],
        "aggregates": aggregates,
        "hypothesis_outcomes": hypothesis,
        "effect_sizes": effect_sizes,
        "integrity": integrity,
    }, indent=2))
    return 0 if all(integrity.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
