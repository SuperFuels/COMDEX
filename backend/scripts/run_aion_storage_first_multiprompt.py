#!/usr/bin/env python3
"""Randomized multi-prompt sustained validation for storage-first Granite MoE."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import gc
import hashlib
import json
from pathlib import Path
import random
import statistics
import time
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, LogitsProcessor

from backend.modules.aion_inference import (
    AdaptiveInferenceRuntime,
    ExpertRouteCorpus,
    verify_expert_working_set_dictionary,
)
from backend.scripts.run_aion_layer_pack_experiment import PackedLayerScopedStore
from backend.scripts.run_aion_layer_scoped_moe_experiment import (
    LayerAheadCoordinator,
    _chat_tokens,
    _layer_scoped_forward,
)
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256
from backend.scripts.run_aion_storage_first_boot import (
    _load_storage_first_model,
    _memory,
    _verify_source_checkpoint,
)


PROMPTS = (
    {
        "family": "commercial_risk",
        "prompt": (
            "A supplier asks us to accept an unverified quotation and pay immediately. "
            "Explain the risks and give at least eight concrete safeguards, with a short "
            "explanation of why each safeguard matters."
        ),
    },
    {
        "family": "technical_explanation",
        "prompt": (
            "Explain in detail why content hashes and fail-closed verification matter when "
            "loading model experts from removable storage. Give at least eight numbered "
            "points covering corruption, substitution, partial reads, manifests, recovery, "
            "audit evidence, performance trade-offs, and operational safety."
        ),
    },
    {
        "family": "business_planning",
        "prompt": (
            "Create a detailed ten-step plan for a small business to introduce a private AI "
            "assistant while retaining human approval for every payment. Explain the purpose, "
            "risk control, and success measure for every step."
        ),
    },
    {
        "family": "cache_diagnosis",
        "prompt": (
            "Write a detailed diagnostic guide for a cache that is fast on repeated requests "
            "but slow on new requests. Include at least ten measurements or experiments, what "
            "each result would mean, and the safe optimisation decision that follows."
        ),
    },
)


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _nearest_rank_p95(values: list[float]) -> float:
    if not values:
        raise ValueError("p95 requires observations")
    return sorted(values)[max(0, int(0.95 * len(values) + 0.999999) - 1)]


def _step_error_summary(errors: list[float], token_ids: list[int]) -> dict[str, Any]:
    """Retain bounded localization evidence without serializing full logits."""
    nonzero = [
        {"step_index": index, "maximum_absolute_error": error, "selected_token_id": token_ids[index]}
        for index, error in enumerate(errors)
        if error != 0.0
    ]
    maximum_index = max(
        (index for index, error in enumerate(errors) if error != 0.0),
        key=errors.__getitem__,
        default=None,
    )
    return {
        "nonzero_step_logit_error_count": len(nonzero),
        "first_nonzero_step_logit_error": nonzero[0] if nonzero else None,
        "maximum_step_logit_error_index": maximum_index,
        "nonzero_step_logit_errors": nonzero,
    }


def _first_token_mismatch(actual: list[int], expected: list[int]) -> int | None:
    for index, (actual_token, expected_token) in enumerate(zip(actual, expected)):
        if actual_token != expected_token:
            return index
    return min(len(actual), len(expected)) if len(actual) != len(expected) else None


def _valid_generation_termination(
    token_ids: list[int], requested_limit: int, eos_token_id: int | None
) -> bool:
    return len(token_ids) == requested_limit or bool(
        token_ids and eos_token_id is not None and token_ids[-1] == eos_token_id
    )


def _validate_prompt_catalog(value: Any) -> tuple[dict[str, str], ...]:
    if not isinstance(value, dict) or value.get("schema_version") != "aion.prompt_manifest.v1":
        raise ValueError("prompt manifest schema must be aion.prompt_manifest.v1")
    prompts = value.get("prompts")
    if not isinstance(prompts, list) or not prompts:
        raise ValueError("prompt manifest must contain a non-empty prompts list")
    catalog: list[dict[str, str]] = []
    families: set[str] = set()
    for index, item in enumerate(prompts):
        if not isinstance(item, dict):
            raise ValueError(f"prompt manifest entry {index} must be an object")
        family = item.get("family")
        prompt = item.get("prompt")
        if not isinstance(family, str) or not family.strip():
            raise ValueError(f"prompt manifest entry {index} has no family")
        if family in families:
            raise ValueError(f"duplicate prompt family: {family}")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"prompt manifest entry {index} has no prompt")
        families.add(family)
        catalog.append({"family": family, "prompt": prompt})
    return tuple(catalog)


def _select_prompts(
    families: list[str] | None,
    seed: int,
    catalog: tuple[dict[str, str], ...] = PROMPTS,
) -> list[dict[str, str]]:
    available = {item["family"]: item for item in catalog}
    requested = list(available) if not families else list(dict.fromkeys(families))
    unknown = sorted(set(requested) - set(available))
    if unknown:
        raise ValueError(f"unknown prompt families: {', '.join(unknown)}")
    selected = [dict(available[family]) for family in requested]
    random.Random(seed).shuffle(selected)
    return selected


class _Timeline(LogitsProcessor):
    def __init__(self) -> None:
        self.started = time.perf_counter()
        self.calls: list[float] = []

    def __call__(self, input_ids, scores):
        self.calls.append(time.perf_counter())
        return scores


def _generate(model, tokenizer, prompt: str, generated_tokens: int) -> dict[str, Any]:
    inputs = _chat_tokens(tokenizer, prompt)
    timeline = _Timeline()
    started = timeline.started
    with torch.inference_mode():
        generated = model.generate(
            **inputs,
            do_sample=False,
            max_new_tokens=generated_tokens,
            use_cache=True,
            return_dict_in_generate=True,
            output_scores=True,
            logits_processor=[timeline],
            pad_token_id=tokenizer.eos_token_id,
        )
    torch.mps.synchronize()
    finished = time.perf_counter()
    continuation = generated.sequences[0, inputs["input_ids"].shape[1]:].detach().cpu()
    call_times = timeline.calls
    intervals = [later - earlier for earlier, later in zip(call_times, call_times[1:])]
    if call_times:
        intervals.append(finished - call_times[-1])
    return {
        "token_ids": continuation.tolist(),
        "text": tokenizer.decode(continuation),
        "scores": [score[0].detach().float().cpu() for score in generated.scores],
        "seconds": finished - started,
        "time_to_first_token_seconds": call_times[0] - started if call_times else None,
        "median_subsequent_token_interval_seconds": statistics.median(intervals) if intervals else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--shard-manifest", type=Path, required=True)
    parser.add_argument("--pack-manifest", type=Path, required=True)
    parser.add_argument("--route-corpus", type=Path, required=True)
    parser.add_argument("--working-set-dictionary", type=Path)
    parser.add_argument(
        "--prompt-manifest",
        type=Path,
        help="Hash-bound external prompt catalog using schema aion.prompt_manifest.v1.",
    )
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--memory-budget-gib", type=float, default=3.0)
    parser.add_argument("--generated-tokens", type=int, default=64)
    parser.add_argument(
        "--zstd-decode-workers",
        type=int,
        help="Bounded shared decoder pool for compressed expert packs.",
    )
    parser.add_argument(
        "--prompt-family",
        action="append",
        dest="prompt_families",
        help="Limit a diagnostic run to one or more named prompt families.",
    )
    parser.add_argument("--seed", type=int, default=20260906)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if not torch.backends.mps.is_available():
        raise SystemExit("Apple Metal/MPS is required")
    if args.generated_tokens < 1 or args.memory_budget_gib <= 0:
        raise SystemExit("generated tokens and memory budget must be positive")
    if args.zstd_decode_workers is not None and args.zstd_decode_workers < 2:
        raise SystemExit("zstd decode workers must be at least two")
    root = args.storage_root.resolve()
    paths = {
        "model": args.model_path.resolve(),
        "shards": args.shard_manifest.resolve(),
        "packs": args.pack_manifest.resolve(),
        "route_corpus": args.route_corpus.resolve(),
    }
    if args.working_set_dictionary:
        paths["working_set_dictionary"] = args.working_set_dictionary.resolve()
    if args.prompt_manifest:
        paths["prompt_manifest"] = args.prompt_manifest.resolve()
    output = (args.output or root / "experiments" / f"{args.run_id}.json").resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all artifacts must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")

    shards = json.loads(paths["shards"].read_text(encoding="utf-8"))
    packs = json.loads(paths["packs"].read_text(encoding="utf-8"))
    if not all(shards["integrity"].values()) or not all(packs["integrity"].values()):
        raise RuntimeError("manifest integrity gate failed")
    if packs["source_manifest_sha256"] != _sha256(paths["shards"]):
        raise RuntimeError("pack/source binding failed")
    source_verification = _verify_source_checkpoint(root, shards)
    if not source_verification["passed"]:
        raise RuntimeError("source checkpoint verification failed closed")

    indexes = []
    entries_by_layer = []
    for number, layer in enumerate(shards["layers"]):
        index_path = Path(layer["index_path"])
        if root not in index_path.resolve().parents or _sha256(index_path) != layer["index_sha256"]:
            raise RuntimeError(f"layer index verification failed: {number}")
        index = json.loads(index_path.read_text(encoding="utf-8"))
        indexes.append(index)
        entries_by_layer.append({int(entry["expert"]): entry for entry in index["experts"]})

    stores = []
    zstd_decode_executor = (
        ThreadPoolExecutor(
            max_workers=args.zstd_decode_workers,
            thread_name_prefix="aion-zstd-decode",
        )
        if args.zstd_decode_workers is not None else None
    )
    pack_verify_started = time.perf_counter()
    for number, (index, pack_layer) in enumerate(zip(indexes, packs["layers"], strict=True)):
        store = PackedLayerScopedStore(number, index, pack_layer)
        store.zstd_decode_executor = zstd_decode_executor
        store.preverify(root)
        stores.append(store)
    pack_verification_seconds = time.perf_counter() - pack_verify_started

    corpus = ExpertRouteCorpus(paths["route_corpus"])
    observations = tuple(sorted(path.stem for path in corpus.objects.glob("*.json")))
    loaded_observations = [corpus.load(digest) for digest in observations]
    working_set_dictionary = None
    if args.working_set_dictionary:
        working_set_dictionary = json.loads(
            paths["working_set_dictionary"].read_text(encoding="utf-8")
        )
        verify_expert_working_set_dictionary(
            working_set_dictionary,
            expected_bindings=loaded_observations[0]["bindings"],
        )
    plan = corpus.optimize_memory(
        observations,
        entries_by_layer,
        maximum_resident_bytes=int(args.memory_budget_gib * 1024**3),
    )
    try:
        prompt_catalog = (
            _validate_prompt_catalog(
                json.loads(paths["prompt_manifest"].read_text(encoding="utf-8"))
            )
            if args.prompt_manifest else PROMPTS
        )
        prompt_order = _select_prompts(args.prompt_families, args.seed, prompt_catalog)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    runtime_root = root / "runtime-evidence" / args.run_id
    runtime = AdaptiveInferenceRuntime(
        replay_path=runtime_root / "replay.sqlite3",
        trace_path=runtime_root / "trace.jsonl",
    )
    requests = []
    for item in prompt_order:
        routed = runtime.route(item["prompt"])
        if not routed.model_call_required or not routed.fallback_prompt:
            raise RuntimeError(f"prompt did not reach model fallback: {item['family']}")
        requests.append({
            **item,
            "model_input": routed.fallback_prompt,
            "glyph_address": routed.glyph_address,
            "proof_receipt_sha256": routed.proof_receipt["proof_receipt_sha256"],
            "model_prompt_schema_version": routed.proof_receipt.get(
                "model_prompt_schema_version", "legacy"
            ),
        })
    model_input_hashes = {
        hashlib.sha256(request["model_input"].encode()).hexdigest()
        for request in requests
    }
    if len(model_input_hashes) != len(requests):
        raise RuntimeError("distinct public prompts collapsed to duplicate model inputs")

    tokenizer = AutoTokenizer.from_pretrained(paths["model"], local_files_only=True)
    for request in requests:
        encoded = tokenizer.apply_chat_template(
            [{"role": "user", "content": request["model_input"]}],
            add_generation_prompt=True,
            tokenize=True,
        )
        request["model_input_tokens"] = len(
            encoded["input_ids"] if hasattr(encoded, "keys") else encoded
        )
    memory = [_memory("before_full_control_load")]
    control_load_started = time.perf_counter()
    control_model = AutoModelForCausalLM.from_pretrained(
        paths["model"], local_files_only=True, dtype=torch.float16,
        device_map={"": "mps"}, low_cpu_mem_usage=True,
    ).eval()
    torch.mps.synchronize()
    control_load_seconds = time.perf_counter() - control_load_started
    memory.append(_memory("after_full_control_load"))
    controls = [
        _generate(control_model, tokenizer, request["model_input"], args.generated_tokens)
        for request in requests
    ]
    del control_model
    gc.collect()
    torch.mps.empty_cache()
    memory.append(_memory("after_full_control_release"))

    model_index = json.loads(
        (paths["model"] / "model.safetensors.index.json").read_text(encoding="utf-8")
    )
    model, boot = _load_storage_first_model(paths["model"], model_index)
    memory.append(_memory("after_storage_first_shared_load"))
    coordinator = LayerAheadCoordinator(stores, tuple(() for _ in stores))
    for layer_number, (layer, store, capacity) in enumerate(zip(
        model.model.layers, stores, plan.capacities_by_layer, strict=True
    )):
        layer.block_sparse_moe.forward = _layer_scoped_forward(
            layer.block_sparse_moe,
            store,
            coordinator,
            retention_capacity=capacity,
            working_set_dictionary=(
                working_set_dictionary["layers"][layer_number]
                if working_set_dictionary is not None else None
            ),
        )

    results = []
    for request, control in zip(requests, controls, strict=True):
        event_starts = [len(store.events) for store in stores]
        observed = _generate(model, tokenizer, request["model_input"], args.generated_tokens)
        events = [
            event
            for store, start in zip(stores, event_starts, strict=True)
            for event in store.events[start:]
            if event["kind"] == "layer_activation"
        ]
        common_score_count = min(len(observed["scores"]), len(control["scores"]))
        errors = [
            float((actual - expected).abs().max().item())
            for actual, expected in zip(
                observed["scores"][:common_score_count],
                control["scores"][:common_score_count],
                strict=True,
            )
        ]
        error_summary = _step_error_summary(errors, observed["token_ids"])
        token_ids_exact_match = observed["token_ids"] == control["token_ids"]
        score_count_exact_match = len(observed["scores"]) == len(control["scores"])
        ended_with_exact_eos = bool(
            token_ids_exact_match
            and observed["token_ids"]
            and tokenizer.eos_token_id is not None
            and observed["token_ids"][-1] == tokenizer.eos_token_id
        )
        results.append({
            "family": request["family"],
            "glyph_address": request["glyph_address"],
            "proof_receipt_sha256": request["proof_receipt_sha256"],
            "model_input_sha256": hashlib.sha256(request["model_input"].encode()).hexdigest(),
            "model_input_utf8_bytes": len(request["model_input"].encode("utf-8")),
            "model_input_tokens": request["model_input_tokens"],
            "model_prompt_schema_version": request["model_prompt_schema_version"],
            "seconds": observed["seconds"],
            "tokens_per_second": len(observed["token_ids"]) / observed["seconds"],
            "time_to_first_token_seconds": observed["time_to_first_token_seconds"],
            "median_subsequent_token_interval_seconds": observed["median_subsequent_token_interval_seconds"],
            "token_ids": observed["token_ids"],
            "text": observed["text"],
            "control_generated_token_count": len(control["token_ids"]),
            "observed_generated_token_count": len(observed["token_ids"]),
            "termination_reason": "exact_eos" if ended_with_exact_eos else "token_limit",
            "first_token_mismatch_index": _first_token_mismatch(
                observed["token_ids"], control["token_ids"]
            ),
            "token_ids_exact_match": token_ids_exact_match,
            "score_count_exact_match": score_count_exact_match,
            "common_step_logit_count": common_score_count,
            "all_step_logits_exact_match": (
                score_count_exact_match and all(error == 0.0 for error in errors)
            ),
            "maximum_step_logit_error": max(errors, default=0.0),
            **error_summary,
            "demand_faults": sum(int(event["demand_faults"]) for event in events),
            "retained_hits": sum(int(event["retained_hits"]) for event in events),
            "demand_logical_bytes": sum(int(event["demand_logical_bytes"]) for event in events),
        })

    coordinator.close()
    if zstd_decode_executor is not None:
        zstd_decode_executor.shutdown(wait=True)
    for control in controls:
        control.pop("scores")
    seconds = [float(result["seconds"]) for result in results]
    throughputs = [float(result["tokens_per_second"]) for result in results]
    ttfts = [float(result["time_to_first_token_seconds"]) for result in results]
    total_faults = sum(int(result["demand_faults"]) for result in results)
    total_hits = sum(int(result["retained_hits"]) for result in results)
    aggregate = {
        "prompt_count": len(results),
        "generated_tokens": sum(len(result["token_ids"]) for result in results),
        "median_seconds": statistics.median(seconds),
        "p95_seconds_nearest_rank": _nearest_rank_p95(seconds),
        "median_tokens_per_second": statistics.median(throughputs),
        "minimum_tokens_per_second": min(throughputs),
        "maximum_tokens_per_second": max(throughputs),
        "median_time_to_first_token_seconds": statistics.median(ttfts),
        "p95_time_to_first_token_seconds_nearest_rank": _nearest_rank_p95(ttfts),
        "demand_faults": total_faults,
        "retained_hits": total_hits,
        "retained_hit_rate_percent": 100.0 * total_hits / (total_hits + total_faults),
        "demand_logical_bytes": sum(int(result["demand_logical_bytes"]) for result in results),
        "all_tokens_exact": all(result["token_ids_exact_match"] for result in results),
        "all_logits_exact": all(result["all_step_logits_exact_match"] for result in results),
    }
    integrity = {
        "source_checkpoint_hashes_verified": source_verification["passed"],
        "all_32_layer_packs_verified": len(stores) == 32,
        "all_1280_experts_addressable": sum(len(store.verified) for store in stores) == 1280,
        "exactly_64_checkpoint_expert_tensors_skipped": boot["skipped_expert_tensor_count"] == 64,
        "no_meta_parameters_or_buffers": not boot["remaining_meta_parameters"] and not boot["remaining_meta_buffers"],
        "all_tokens_exact": aggregate["all_tokens_exact"],
        "all_step_logits_exact": aggregate["all_logits_exact"],
        "controller_memory_within_declared_ceiling": plan.estimated_resident_bytes <= plan.maximum_resident_bytes,
        "complete_requested_prompt_order": len(results) == len(prompt_order),
        "all_model_inputs_distinct": len(model_input_hashes) == len(requests),
        "all_prompts_reached_limit_or_exact_eos": all(
            _valid_generation_termination(
                result["token_ids"], args.generated_tokens, tokenizer.eos_token_id
            )
            for result in results
        ),
        "working_set_dictionary_verified_or_not_requested": (
            working_set_dictionary is None
            or working_set_dictionary.get("dictionary_sha256") is not None
        ),
    }
    report = {
        "schema_version": "aion.storage_first_multiprompt.v3",
        "run_id": args.run_id,
        "storage_root": str(root),
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": {
            "shard_manifest": _sha256(paths["shards"]),
            "pack_manifest": _sha256(paths["packs"]),
            "route_corpus_observation_set": _canonical_sha256(observations),
            "working_set_dictionary": (
                _sha256(paths["working_set_dictionary"])
                if working_set_dictionary is not None else None
            ),
            "working_set_dictionary_internal": (
                working_set_dictionary["dictionary_sha256"]
                if working_set_dictionary is not None else None
            ),
            "prompt_manifest": (
                _sha256(paths["prompt_manifest"])
                if args.prompt_manifest else None
            ),
        },
        "method": {
            "seed": args.seed,
            "prompt_order": [request["family"] for request in requests],
            "available_prompt_families": [item["family"] for item in prompt_catalog],
            "diagnostic_subset": len(requests) != len(prompt_catalog),
            "generated_token_ceiling_per_prompt": args.generated_tokens,
            "persistent_cache_across_prompts": True,
            "cache_empty_before_first_prompt": True,
            "cache_condition": "warm_uncontrolled",
            "full_resident_exact_control": True,
            "promotion_run": False,
            "zstd_decode_workers": args.zstd_decode_workers,
            "retention_policy": (
                "predictive_protection_no_speculative_reads"
                if working_set_dictionary is not None else "live_lfu_recency"
            ),
        },
        "verification": {
            "source_checkpoint": source_verification,
            "pack_verification_seconds": pack_verification_seconds,
        },
        "control_load_seconds": control_load_seconds,
        "storage_first_boot": boot,
        "capacity": {
            "maximum_resident_bytes": plan.maximum_resident_bytes,
            "estimated_resident_bytes": plan.estimated_resident_bytes,
            "plan_sha256": plan.plan_sha256,
        },
        "requests": results,
        "controls": controls,
        "aggregate": aggregate,
        "memory": memory,
        "generation_peak": {
            "mps_bytes": coordinator.peak_mps_bytes,
            "rss_bytes": coordinator.peak_rss_bytes,
        },
        "integrity": integrity,
        "validation_passed": all(integrity.values()),
        "claim_boundary": (
            f"{len(requests)} requested prompt families at up to {args.generated_tokens} generated tokens per prompt "
            "with one persistent cache. Filesystem "
            "state is warm uncontrolled and there is one observation per family; this is not "
            "cold-cache or replicated population-level p95 evidence."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "report_sha256": report["report_sha256"],
        "prompt_order": report["method"]["prompt_order"],
        "requests": results,
        "aggregate": aggregate,
        "generation_peak": report["generation_peak"],
        "integrity": integrity,
    }, indent=2))
    return 0 if all(integrity.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
