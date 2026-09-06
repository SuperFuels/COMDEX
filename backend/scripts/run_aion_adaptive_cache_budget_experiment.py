#!/usr/bin/env python3
"""Learn a global per-layer cache budget and test it on held-out prompts."""

from __future__ import annotations

import argparse
from dataclasses import asdict
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
    ExpertRouteCorpus,
    optimize_expert_cache_budget,
)
from backend.scripts.run_aion_layer_pack_experiment import PackedLayerScopedStore
from backend.scripts.run_aion_layer_scoped_moe_experiment import (
    LayerAheadCoordinator,
    _chat_tokens,
    _layer_scoped_forward,
)
from backend.scripts.run_aion_moe_end_to_end_fault_in import _memory_snapshot, _sha256


TRAINING_CASE = {
    "prompt": "Human review is required and payment is forbidden. What can happen next?",
    "generated_tokens": 16,
}
CORPUS_TRAINING_CASES = (
    TRAINING_CASE,
    {
        "prompt": "Explain why dividing a quantity into four equal parts produces quarters.",
        "generated_tokens": 16,
    },
    {
        "prompt": "Write a Python function that returns the absolute difference between two integers.",
        "generated_tokens": 16,
    },
)
HELD_OUT_CASES = (
    {
        "prompt": "Explain how a 7 percent tax changes a quoted price without calculating it.",
        "generated_tokens": 12,
        "order": ("uniform_16", "adaptive_512"),
    },
    {
        "prompt": "Write a Python function that returns the larger of two integers.",
        "generated_tokens": 12,
        "order": ("adaptive_512", "uniform_16"),
    },
)


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
    parser.add_argument("--total-capacity", type=int, default=512)
    parser.add_argument(
        "--training-corpus",
        action="store_true",
        help="learn from three prompt-private route observations instead of one prompt",
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
    training_cases = CORPUS_TRAINING_CASES if args.training_corpus else (TRAINING_CASE,)
    cases = [*training_cases, *HELD_OUT_CASES]
    requests = []
    for case in cases:
        routed = runtime.route(case["prompt"])
        if not routed.model_call_required or not routed.fallback_prompt:
            raise RuntimeError("experiment case did not reach model fallback")
        requests.append({
            "public_prompt": case["prompt"],
            "model_input": routed.fallback_prompt,
            "model_input_sha256": hashlib.sha256(routed.fallback_prompt.encode()).hexdigest(),
            "glyph_address": routed.glyph_address,
            "proof_receipt_sha256": routed.proof_receipt["proof_receipt_sha256"],
            "generated_tokens": case["generated_tokens"],
        })

    load_started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(paths["model"], local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        paths["model"], local_files_only=True, dtype=torch.float16,
        device_map={"": "mps"}, low_cpu_mem_usage=True,
    ).eval()
    checkpoint_load_seconds = time.perf_counter() - load_started

    def generate(request: dict[str, Any]) -> dict[str, Any]:
        inputs = _chat_tokens(tokenizer, request["model_input"])
        began = time.perf_counter()
        with torch.inference_mode():
            generated = model.generate(
                **inputs, do_sample=False, max_new_tokens=request["generated_tokens"],
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

    controls = [generate(request) for request in requests]
    unrestricted_memory = _memory_snapshot("after_unrestricted")
    layers = list(model.model.layers)
    stores = []
    verification_started = time.perf_counter()
    for number, (layer, shard_layer, pack_layer) in enumerate(
        zip(layers, shards["layers"], packs["layers"], strict=True)
    ):
        index_path = Path(shard_layer["index_path"])
        if root not in index_path.resolve().parents or _sha256(index_path) != shard_layer["index_sha256"]:
            raise RuntimeError(f"index integrity failed: layer {number}")
        store = PackedLayerScopedStore(
            number, json.loads(index_path.read_text(encoding="utf-8")), pack_layer
        )
        store.preverify(root)
        stores.append(store)
        layer.block_sparse_moe.input_linear = None
        layer.block_sparse_moe.output_linear = None
    verification_seconds = time.perf_counter() - verification_started
    gc.collect()
    torch.mps.empty_cache()
    stripped_memory = _memory_snapshot("expert_tensors_removed")

    def run_condition(
        request: dict[str, Any],
        control: dict[str, Any],
        capacities: tuple[int, ...],
        condition: str,
    ) -> dict[str, Any]:
        for store in stores:
            store.clear_all()
        gc.collect()
        torch.mps.empty_cache()
        event_starts = [len(store.events) for store in stores]
        open_start = sum(store.pack_opens for store in stores)
        coordinator = LayerAheadCoordinator(stores, tuple(() for _ in stores))
        for layer, store, capacity in zip(layers, stores, capacities, strict=True):
            layer.block_sparse_moe.forward = _layer_scoped_forward(
                layer.block_sparse_moe, store, coordinator, retention_capacity=capacity
            )
        result = generate(request)
        coordinator.close()
        events = [
            event for store, start in zip(stores, event_starts, strict=True)
            for event in store.events[start:] if event["kind"] == "layer_activation"
        ]
        errors = [
            float((observed - expected).abs().max().item())
            for observed, expected in zip(result["scores"], control["scores"], strict=True)
        ]
        return {
            "condition": condition,
            "seconds": result["seconds"],
            "peak_mps_bytes": coordinator.peak_mps_bytes,
            "peak_rss_bytes": coordinator.peak_rss_bytes,
            "retained_experts_after_generation": sum(len(store.retained) for store in stores),
            "retained_hits": sum(event["retained_hits"] for event in events),
            "demand_faults": sum(event["demand_faults"] for event in events),
            "demand_logical_bytes": sum(event["demand_logical_bytes"] for event in events),
            "pack_open_operations": sum(store.pack_opens for store in stores) - open_start,
            "token_ids": result["token_ids"],
            "text": result["text"],
            "token_ids_exact_match": result["token_ids"] == control["token_ids"],
            "all_step_logits_exact_match": all(error == 0.0 for error in errors),
            "maximum_step_logit_error": max(errors, default=0.0),
        }

    uniform_capacities = tuple(args.total_capacity // len(stores) for _ in stores)
    training_trials = []
    training_route_sets = []
    for training_number, (request, control) in enumerate(
        zip(requests[:len(training_cases)], controls[:len(training_cases)], strict=True)
    ):
        trial = run_condition(
            request, control, uniform_capacities, f"training_uniform_{training_number}"
        )
        trial["training_case_number"] = training_number
        training_trials.append(trial)
        training_routes = tuple(tuple(store.route_batches) for store in stores)
        if any(not layer_batches for layer_batches in training_routes):
            raise RuntimeError("training route capture is incomplete")
        training_route_sets.append(training_routes)

    corpus_observation_sha256s = []
    corpus_root = root / "route-corpora" / args.run_id
    if args.training_corpus:
        corpus = ExpertRouteCorpus(corpus_root)
        model_config_sha256 = _sha256(paths["model"] / "config.json")
        shard_manifest_sha256 = _sha256(paths["shards"])
        pack_manifest_sha256 = _sha256(paths["packs"])
        for request, trial, training_routes in zip(
            requests[:len(training_cases)], training_trials, training_route_sets, strict=True
        ):
            if not trial["token_ids_exact_match"] or not trial["all_step_logits_exact_match"]:
                raise RuntimeError("refusing to record a non-equivalent route observation")
            corpus_observation_sha256s.append(corpus.record(
                route_batches_by_layer=training_routes,
                glyph_address=request["glyph_address"],
                model_input_sha256=request["model_input_sha256"],
                generated_tokens=request["generated_tokens"],
                model_config_sha256=model_config_sha256,
                shard_manifest_sha256=shard_manifest_sha256,
                pack_manifest_sha256=pack_manifest_sha256,
                experts_per_layer=len(stores[0].entries),
            ))
        budget_plan = corpus.optimize(
            corpus_observation_sha256s,
            tuple(store.entries for store in stores),
            total_capacity=args.total_capacity,
        )
    else:
        budget_plan = optimize_expert_cache_budget(
            training_route_sets[0],
            tuple(store.entries for store in stores),
            total_capacity=args.total_capacity,
        )
    adaptive_capacities = budget_plan.capacities_by_layer

    trials = []
    for case_number, (case, request, control) in enumerate(
        zip(
            HELD_OUT_CASES,
            requests[len(training_cases):],
            controls[len(training_cases):],
            strict=True,
        )
    ):
        for condition in case["order"]:
            capacities = uniform_capacities if condition == "uniform_16" else adaptive_capacities
            trial = run_condition(request, control, capacities, condition)
            trial.update({
                "case_number": case_number,
                "public_prompt": case["prompt"],
                "generated_tokens": case["generated_tokens"],
                "sequence_within_case": list(case["order"]).index(condition),
            })
            trials.append(trial)

    for control in controls:
        control.pop("scores")
    aggregates = {}
    for condition in ("uniform_16", "adaptive_512"):
        group = [trial for trial in trials if trial["condition"] == condition]
        aggregates[condition] = {
            "median_seconds": statistics.median(trial["seconds"] for trial in group),
            "maximum_peak_mps_bytes": max(trial["peak_mps_bytes"] for trial in group),
            "total_demand_faults": sum(trial["demand_faults"] for trial in group),
            "total_demand_logical_bytes": sum(trial["demand_logical_bytes"] for trial in group),
            "total_retained_hits": sum(trial["retained_hits"] for trial in group),
            "all_outputs_exact": all(
                trial["token_ids_exact_match"] and trial["all_step_logits_exact_match"]
                for trial in group
            ),
        }
    uniform, adaptive = aggregates["uniform_16"], aggregates["adaptive_512"]
    outcomes = {
        "adaptive_time_change_percent_vs_uniform": 100.0 * (
            adaptive["median_seconds"] / uniform["median_seconds"] - 1.0
        ),
        "adaptive_peak_mps_change_percent_vs_uniform": 100.0 * (
            adaptive["maximum_peak_mps_bytes"] / uniform["maximum_peak_mps_bytes"] - 1.0
        ),
        "adaptive_demand_byte_reduction_percent_vs_uniform": 100.0 * (
            1.0 - adaptive["total_demand_logical_bytes"] / uniform["total_demand_logical_bytes"]
        ),
        "adaptive_improves_held_out_demand_bytes": (
            adaptive["total_demand_logical_bytes"] < uniform["total_demand_logical_bytes"]
        ),
        "adaptive_improves_held_out_median_time": (
            adaptive["median_seconds"] < uniform["median_seconds"]
        ),
    }
    integrity = {
        "training_and_two_held_out_cases_completed": len(trials) == 4,
        "requested_training_cases_completed": len(training_trials) == len(training_cases),
        "corpus_observations_content_addressed": (
            not args.training_corpus
            or len(corpus_observation_sha256s) == len(training_cases)
            and len(set(corpus_observation_sha256s)) == len(training_cases)
            and all(len(digest) == 64 for digest in corpus_observation_sha256s)
        ),
        "opposite_held_out_condition_orders_completed": (
            [trial["condition"] for trial in trials]
            == ["uniform_16", "adaptive_512", "adaptive_512", "uniform_16"]
        ),
        "global_capacity_exactly_512": sum(adaptive_capacities) == args.total_capacity == 512,
        "all_32_layer_packs_verified": len(stores) == 32,
        "all_1280_experts_addressable": sum(len(store.verified) for store in stores) == 1280,
        "all_token_ids_and_step_logits_exact": (
            all(
                trial["token_ids_exact_match"] and trial["all_step_logits_exact_match"]
                for trial in training_trials
            )
            and all(
                trial["token_ids_exact_match"] and trial["all_step_logits_exact_match"]
                for trial in trials
            )
        ),
        "all_artifacts_on_external_storage": all(
            root in path.parents for path in (*paths.values(), output)
        ) and (not args.training_corpus or root in corpus_root.parents),
    }
    report = {
        "schema_version": (
            "aion.adaptive_cache_budget_experiment.v2"
            if args.training_corpus
            else "aion.adaptive_cache_budget_experiment.v1"
        ),
        "run_id": args.run_id,
        "storage_root": str(root),
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": {name: _sha256(path) for name, path in paths.items() if path.is_file()},
        "gateway_trace_path": str(evidence_root / "trace.jsonl"),
        "gateway_trace_sha256": _sha256(evidence_root / "trace.jsonl"),
        "method": {
            "training_cases": training_cases,
            "prompt_private_route_corpus": args.training_corpus,
            "held_out_cases": HELD_OUT_CASES,
            "global_expert_capacity": args.total_capacity,
            "uniform_capacity_per_layer": args.total_capacity // len(stores),
            "objective": "minimize simulated logical demand bytes on training route batches",
            "same_loaded_model": True,
            "os_file_cache_controlled": False,
        },
        "requests": [{k: v for k, v in request.items() if k != "model_input"} for request in requests],
        "controls": controls,
        "training_trials": training_trials,
        "route_corpus": {
            "root": str(corpus_root) if args.training_corpus else None,
            "observation_sha256s": corpus_observation_sha256s,
            "prompt_text_stored": False,
            "model_output_stored": False,
        },
        "budget_plan": asdict(budget_plan),
        "trials": trials,
        "aggregates": aggregates,
        "outcomes": outcomes,
        "timing": {
            "checkpoint_load_seconds": checkpoint_load_seconds,
            "manifest_verification_seconds": verification_seconds,
        },
        "memory": {"unrestricted": unrestricted_memory, "experts_removed": stripped_memory},
        "integrity": integrity,
        "claim_boundary": (
            f"The allocation was learned from {len(training_cases)} prompt-private route "
            "observation(s) and tested on two held-out prompts under "
            "opposite condition orders. This is a transfer probe, not population-level proof; OS "
            "file cache, physical SD reads and thermal state were not controlled."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output), "report_sha256": report["report_sha256"],
        "budget_plan": asdict(budget_plan), "aggregates": aggregates,
        "outcomes": outcomes, "integrity": integrity,
    }, indent=2))
    return 0 if all(integrity.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
