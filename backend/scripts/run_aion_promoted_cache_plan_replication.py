#!/usr/bin/env python3
"""Replicate a promoted cache plan on a broader held-out prompt set."""

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

from backend.modules.aion_inference import AdaptiveInferenceRuntime, verify_promoted_expert_cache_plan
from backend.scripts.run_aion_layer_pack_experiment import PackedLayerScopedStore
from backend.scripts.run_aion_layer_scoped_moe_experiment import (
    LayerAheadCoordinator,
    _chat_tokens,
    _layer_scoped_forward,
)
from backend.scripts.run_aion_moe_end_to_end_fault_in import _memory_snapshot, _sha256


CASES = (
    {
        "prompt": "Compare two approaches to reducing customer support response time and state one tradeoff.",
        "generated_tokens": 16,
        "order": ("uniform_16", "promoted_512"),
    },
    {
        "prompt": "Explain why multiplying a price by 1.2 represents a 20 percent markup without calculating a final price.",
        "generated_tokens": 16,
        "order": ("promoted_512", "uniform_16"),
    },
    {
        "prompt": "Write a Python function that determines whether an integer is even.",
        "generated_tokens": 16,
        "order": ("promoted_512", "uniform_16"),
    },
    {
        "prompt": "Give a reversible three-step plan for migrating a small database with human approval before cutover.",
        "generated_tokens": 16,
        "order": ("uniform_16", "promoted_512"),
    },
)
LONGER_CASES = (
    {
        "prompt": "Explain how to handle a refund request when approval is required and no irreversible action is allowed.",
        "generated_tokens": 24,
    },
    {
        "prompt": "Explain why increasing a quantity by one quarter is equivalent to multiplying it by 1.25, without evaluating a final example.",
        "generated_tokens": 24,
    },
    {
        "prompt": "Write a Python function that returns the second largest distinct integer in a list, or None when it does not exist.",
        "generated_tokens": 24,
    },
    {
        "prompt": "Propose a reversible four-step rollout for a small service, including monitoring and explicit human approval before full release.",
        "generated_tokens": 24,
    },
)


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _comparison_cases(
    *, direct_comparison: bool, longer_corpus: bool
) -> tuple[str, str, tuple[dict[str, Any], ...]]:
    first_condition = "reference_512" if direct_comparison else "uniform_16"
    second_condition = "candidate_512" if direct_comparison else "promoted_512"
    if not direct_comparison and not longer_corpus:
        return first_condition, second_condition, CASES
    base_cases = LONGER_CASES if longer_corpus else CASES
    cases = tuple({
        **case,
        "order": (
            (first_condition, second_condition)
            if number % 2 == 0
            else (second_condition, first_condition)
        ),
    } for number, case in enumerate(base_cases))
    return first_condition, second_condition, cases


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--shard-manifest", type=Path, required=True)
    parser.add_argument("--pack-manifest", type=Path, required=True)
    parser.add_argument("--cache-plan", type=Path, required=True)
    parser.add_argument("--challenger-cache-plan", type=Path)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--case-index", type=int)
    parser.add_argument("--abba", action="store_true")
    parser.add_argument("--longer-corpus", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    direct_comparison = args.challenger_cache_plan is not None
    first_condition, second_condition, selected_cases = _comparison_cases(
        direct_comparison=direct_comparison, longer_corpus=args.longer_corpus
    )
    if args.case_index is not None:
        if args.case_index < 0 or args.case_index >= len(selected_cases):
            raise SystemExit("case index outside replication corpus")
        selected = dict(selected_cases[args.case_index])
        if args.abba:
            selected["order"] = (
                first_condition, second_condition, second_condition, first_condition
            )
        selected_cases = (selected,)

    root = args.storage_root.resolve()
    paths = {
        "model": args.model_path.resolve(), "profile": args.profile.resolve(),
        "shards": args.shard_manifest.resolve(), "packs": args.pack_manifest.resolve(),
        "cache_plan": args.cache_plan.resolve(),
    }
    if args.challenger_cache_plan is not None:
        paths["challenger_cache_plan"] = args.challenger_cache_plan.resolve()
    output = (args.output or root / "experiments" / f"{args.run_id}.json").resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all artifacts must reside on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    if not torch.backends.mps.is_available():
        raise SystemExit("Apple Metal/MPS is required")

    shards = json.loads(paths["shards"].read_text(encoding="utf-8"))
    packs = json.loads(paths["packs"].read_text(encoding="utf-8"))
    plan_document = json.loads(paths["cache_plan"].read_text(encoding="utf-8"))
    if not all(shards["integrity"].values()) or not all(packs["integrity"].values()):
        raise RuntimeError("manifest integrity gate failed")
    promoted_capacities = verify_promoted_expert_cache_plan(
        plan_document,
        expected_model_config_sha256=_sha256(paths["model"] / "config.json"),
        expected_shard_manifest_sha256=_sha256(paths["shards"]),
        expected_pack_manifest_sha256=_sha256(paths["packs"]),
    )
    uniform_capacities = tuple(16 for _ in promoted_capacities)
    capacities_by_condition = {
        "uniform_16": uniform_capacities,
        "promoted_512": promoted_capacities,
    }
    if direct_comparison:
        challenger_document = json.loads(
            paths["challenger_cache_plan"].read_text(encoding="utf-8")
        )
        challenger_capacities = verify_promoted_expert_cache_plan(
            challenger_document,
            expected_model_config_sha256=_sha256(paths["model"] / "config.json"),
            expected_shard_manifest_sha256=_sha256(paths["shards"]),
            expected_pack_manifest_sha256=_sha256(paths["packs"]),
        )
        capacities_by_condition = {
            "reference_512": promoted_capacities,
            "candidate_512": challenger_capacities,
        }
    if any(sum(capacities) != 512 for capacities in capacities_by_condition.values()):
        raise RuntimeError("cache-plan budgets differ or do not equal 512")

    evidence_root = root / "runtime-evidence" / args.run_id
    runtime = AdaptiveInferenceRuntime(
        replay_path=evidence_root / "replay.sqlite3",
        trace_path=evidence_root / "trace.jsonl",
    )
    requests = []
    for case in selected_cases:
        routed = runtime.route(case["prompt"])
        if not routed.model_call_required or not routed.fallback_prompt:
            raise RuntimeError("replication case did not reach model fallback")
        requests.append({
            "public_prompt": case["prompt"], "model_input": routed.fallback_prompt,
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
            "token_ids": continuation.tolist(), "text": tokenizer.decode(continuation),
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

    def run_condition(request, control, condition, capacities):
        for store in stores:
            store.clear_all()
        gc.collect()
        torch.mps.empty_cache()
        starts = [len(store.events) for store in stores]
        opens = sum(store.pack_opens for store in stores)
        coordinator = LayerAheadCoordinator(stores, tuple(() for _ in stores))
        for layer, store, capacity in zip(layers, stores, capacities, strict=True):
            layer.block_sparse_moe.forward = _layer_scoped_forward(
                layer.block_sparse_moe, store, coordinator, retention_capacity=capacity
            )
        result = generate(request)
        coordinator.close()
        events = [
            event for store, start in zip(stores, starts, strict=True)
            for event in store.events[start:] if event["kind"] == "layer_activation"
        ]
        errors = [
            float((observed - expected).abs().max().item())
            for observed, expected in zip(result["scores"], control["scores"], strict=True)
        ]
        return {
            "condition": condition, "seconds": result["seconds"],
            "peak_mps_bytes": coordinator.peak_mps_bytes,
            "peak_rss_bytes": coordinator.peak_rss_bytes,
            "retained_experts_after_generation": sum(len(store.retained) for store in stores),
            "retained_hits": sum(event["retained_hits"] for event in events),
            "demand_faults": sum(event["demand_faults"] for event in events),
            "demand_logical_bytes": sum(event["demand_logical_bytes"] for event in events),
            "pack_open_operations": sum(store.pack_opens for store in stores) - opens,
            "token_ids": result["token_ids"], "text": result["text"],
            "token_ids_exact_match": result["token_ids"] == control["token_ids"],
            "all_step_logits_exact_match": all(error == 0.0 for error in errors),
            "maximum_step_logit_error": max(errors, default=0.0),
        }

    trials = []
    for case_number, (case, request, control) in enumerate(
        zip(selected_cases, requests, controls, strict=True)
    ):
        for sequence, condition in enumerate(case["order"]):
            capacities = capacities_by_condition[condition]
            trial = run_condition(request, control, condition, capacities)
            trial.update({
                "case_number": case_number, "sequence_within_case": sequence,
                "public_prompt": case["prompt"], "generated_tokens": case["generated_tokens"],
            })
            trials.append(trial)

    for control in controls:
        control.pop("scores")
    aggregates = {}
    for condition in (first_condition, second_condition):
        group = [trial for trial in trials if trial["condition"] == condition]
        aggregates[condition] = {
            "median_seconds": statistics.median(trial["seconds"] for trial in group),
            "maximum_peak_mps_bytes": max(trial["peak_mps_bytes"] for trial in group),
            "total_demand_faults": sum(trial["demand_faults"] for trial in group),
            "total_demand_logical_bytes": sum(trial["demand_logical_bytes"] for trial in group),
            "total_retained_hits": sum(trial["retained_hits"] for trial in group),
            "wins_by_seconds": 0,
            "all_outputs_exact": all(
                trial["token_ids_exact_match"] and trial["all_step_logits_exact_match"] for trial in group
            ),
        }
    paired = []
    for case_number in range(len(selected_cases)):
        case_trials = [trial for trial in trials if trial["case_number"] == case_number]
        first_case_seconds = statistics.median(
            trial["seconds"] for trial in case_trials if trial["condition"] == first_condition
        )
        second_case_seconds = statistics.median(
            trial["seconds"] for trial in case_trials if trial["condition"] == second_condition
        )
        change = 100.0 * (second_case_seconds / first_case_seconds - 1.0)
        pair = {
            "case_number": case_number,
            "second_condition": second_condition,
            "second_time_change_percent_vs_first": change,
        }
        if not direct_comparison:
            pair["promoted_time_change_percent"] = change
        paired.append(pair)
        if change < 0:
            aggregates[second_condition]["wins_by_seconds"] += 1
        else:
            aggregates[first_condition]["wins_by_seconds"] += 1
    first, second = aggregates[first_condition], aggregates[second_condition]
    outcomes = {
        "comparison": f"{second_condition}_vs_{first_condition}",
        "second_time_change_percent_vs_first": 100.0 * (
            second["median_seconds"] / first["median_seconds"] - 1.0
        ),
        "second_peak_mps_change_percent_vs_first": 100.0 * (
            second["maximum_peak_mps_bytes"] / first["maximum_peak_mps_bytes"] - 1.0
        ),
        "second_demand_byte_reduction_percent_vs_first": 100.0 * (
            1.0 - second["total_demand_logical_bytes"] / first["total_demand_logical_bytes"]
        ),
        "second_condition_case_wins": second["wins_by_seconds"],
        "second_has_lower_median_time": second["median_seconds"] < first["median_seconds"],
        "second_has_lower_demand_bytes": (
            second["total_demand_logical_bytes"] < first["total_demand_logical_bytes"]
        ),
    }
    if not direct_comparison:
        outcomes.update({
            "promoted_time_change_percent_vs_uniform": outcomes[
                "second_time_change_percent_vs_first"
            ],
            "promoted_peak_mps_change_percent_vs_uniform": outcomes[
                "second_peak_mps_change_percent_vs_first"
            ],
            "promoted_demand_byte_reduction_percent_vs_uniform": outcomes[
                "second_demand_byte_reduction_percent_vs_first"
            ],
            "promoted_case_wins": outcomes["second_condition_case_wins"],
            "replicates_lower_median_time": outcomes["second_has_lower_median_time"],
            "replicates_lower_demand_bytes": outcomes["second_has_lower_demand_bytes"],
        })
    expected_order = [condition for case in selected_cases for condition in case["order"]]
    integrity = {
        "requested_cases_and_conditions_completed": len(trials) == len(expected_order),
        "requested_condition_orders_completed": [trial["condition"] for trial in trials] == expected_order,
        "all_cache_plans_verified_against_bound_model_and_manifests": True,
        "equal_512_slot_budgets": all(
            sum(capacities) == 512 for capacities in capacities_by_condition.values()
        ),
        "all_32_layer_packs_verified": len(stores) == 32,
        "all_1280_experts_addressable": sum(len(store.verified) for store in stores) == 1280,
        "all_token_ids_and_step_logits_exact": all(
            trial["token_ids_exact_match"] and trial["all_step_logits_exact_match"] for trial in trials
        ),
        "all_artifacts_on_external_storage": all(root in path.parents for path in (*paths.values(), output)),
    }
    report = {
        "schema_version": (
            "aion.cache_plan_head_to_head.v1"
            if direct_comparison
            else "aion.promoted_cache_plan_replication.v1"
        ),
        "run_id": args.run_id, "storage_root": str(root),
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": {name: _sha256(path) for name, path in paths.items() if path.is_file()},
        "gateway_trace_path": str(evidence_root / "trace.jsonl"),
        "gateway_trace_sha256": _sha256(evidence_root / "trace.jsonl"),
        "method": {
            "cases": selected_cases, "same_loaded_model": True,
            "balanced_condition_order": args.case_index is None or args.abba,
            "equal_global_expert_capacity": 512, "os_file_cache_controlled": False,
            "direct_plan_comparison": direct_comparison,
            "longer_24_token_corpus": args.longer_corpus,
            "first_condition": first_condition,
            "second_condition": second_condition,
        },
        "requests": [{k: v for k, v in request.items() if k != "model_input"} for request in requests],
        "controls": controls, "trials": trials, "paired": paired,
        "aggregates": aggregates, "outcomes": outcomes,
        "timing": {"checkpoint_load_seconds": checkpoint_load_seconds,
                   "manifest_verification_seconds": verification_seconds},
        "memory": {"unrestricted": unrestricted_memory, "experts_removed": stripped_memory},
        "integrity": integrity,
        "claim_boundary": (
            "This balanced-order four-prompt comparison broadens the held-out evidence but does not "
            "establish population-level latency, cold physical SD behavior, energy savings or transfer "
            "to other models, hosts or storage media."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "report_sha256": report["report_sha256"],
                      "paired": paired, "aggregates": aggregates,
                      "outcomes": outcomes, "integrity": integrity}, indent=2))
    return 0 if all(integrity.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
