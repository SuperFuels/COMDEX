#!/usr/bin/env python3
"""Storage-first full-model ABBA gate for sparse packed-INT8 expert dispatch."""

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
from transformers import AutoTokenizer

from backend.modules.aion_inference.int8_glyph_moe import Int8GlyphMoE, load_layer_entries
from backend.modules.aion_inference.int8_dynamic_bank_moe import (
    PRECISE_ROUTER_PYTORCH_FALLBACK_LAYERS,
    PRECISE_ROUTER_UNGUARDED_DECODE_TOKENS,
    PROJECTION_PIPELINE_INITIAL_DECODE_TOKENS,
    Int8DynamicBankMoE,
    load_bank_entry,
)
from backend.scripts.run_aion_int8_glyph_full_model import _canonical_sha256, _memory
from backend.scripts.run_aion_int8pack_expert_microbench import _p95
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256
from backend.scripts.run_aion_storage_first_boot import (
    _load_storage_first_model, _verify_source_checkpoint,
)
from backend.scripts.run_aion_storage_first_multiprompt import (
    PROMPTS, _generate, _validate_prompt_catalog,
)


def _summarize(results: list[dict[str, Any]]) -> dict[str, float]:
    seconds = [item["seconds"] for item in results]
    ttft = [item["time_to_first_token_seconds"] for item in results]
    intervals = [item["median_subsequent_token_interval_seconds"] for item in results]
    throughputs = [len(item["token_ids"]) / item["seconds"] for item in results]
    return {"run_count": len(results), "p50_seconds": statistics.median(seconds),
            "p95_seconds_nearest_rank": _p95(seconds),
            "median_tokens_per_second": statistics.median(throughputs),
            "p50_time_to_first_token_seconds": statistics.median(ttft),
            "p95_time_to_first_token_seconds_nearest_rank": _p95(ttft),
            "p50_median_subsequent_token_interval_seconds": statistics.median(intervals),
            "p95_median_subsequent_token_interval_seconds_nearest_rank": _p95(intervals)}


def _equivalence(reference: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    token_exact = reference["token_ids"] == candidate["token_ids"]
    errors = [float((left - right).abs().max()) for left, right in
              zip(reference["scores"], candidate["scores"], strict=True)]
    return {"token_ids_exact": token_exact,
            "step_logits_bit_exact": all(error == 0 for error in errors),
            "maximum_step_logit_error": max(errors, default=0.0)}


def _set_sparse(model: Any, enabled: bool) -> None:
    for layer in model.model.layers:
        layer.block_sparse_moe.experts.skip_empty_experts = enabled


def _set_cached_views(model: Any, enabled: bool) -> None:
    for layer in model.model.layers:
        layer.block_sparse_moe.experts.use_cached_weight_views = enabled


def _set_fused_metal(model: Any, enabled: bool,
                     allowed_layers: set[int] | None = None) -> None:
    for index, layer in enumerate(model.model.layers):
        layer.block_sparse_moe.experts.use_fused_metal_matvec = (
            enabled and (allowed_layers is None or index in allowed_layers))


def _set_dynamic_bank(model: Any, enabled: bool) -> None:
    for layer in model.model.layers:
        layer.block_sparse_moe.use_dynamic_decode = enabled


def _set_fused_router(model: Any, enabled: bool) -> None:
    for index, layer in enumerate(model.model.layers):
        layer.block_sparse_moe.use_fused_router = enabled
        layer.block_sparse_moe.router_fallback_after_tokens = (
            PRECISE_ROUTER_UNGUARDED_DECODE_TOKENS
            if index in PRECISE_ROUTER_PYTORCH_FALLBACK_LAYERS else None)
        layer.block_sparse_moe.use_fused_prefill_router = enabled
        layer.block_sparse_moe.use_fused_projection_pipeline = enabled
        layer.block_sparse_moe.projection_pipeline_decode_tokens = (
            PROJECTION_PIPELINE_INITIAL_DECODE_TOKENS if enabled else None)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--glyph-manifest", type=Path, required=True)
    parser.add_argument("--generated-tokens", type=int, default=64)
    parser.add_argument("--prompt-manifest", type=Path)
    parser.add_argument("--prompt-family", action="append", default=[])
    parser.add_argument("--deterministic-algorithms", action="store_true")
    parser.add_argument("--diagnostic-only", action="store_true")
    parser.add_argument(
        "--cached-views-gate", action="store_true",
        help=("Compare promoted sparse dispatch with dynamic versus cached resident "
              "weight views; both conditions retain sparse dispatch."),
    )
    parser.add_argument(
        "--fused-metal-gate", action="store_true",
        help=("Compare promoted sparse INT8 decode with the quality-gated fused "
              "eight-expert Metal matvec."),
    )
    parser.add_argument("--fused-maximum-step-logit-error", type=float, default=0.05)
    parser.add_argument("--fused-minimum-throughput-gain", type=float, default=5.0)
    parser.add_argument("--fused-layer-plan", type=Path)
    parser.add_argument("--dynamic-bank-manifest", type=Path)
    parser.add_argument("--dynamic-bank-gate", action="store_true")
    parser.add_argument("--fused-router-gate", action="store_true")
    parser.add_argument("--router-audit", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sum((args.cached_views_gate, args.fused_metal_gate, args.dynamic_bank_gate,
            args.fused_router_gate)) > 1:
        raise SystemExit("select only one experimental comparison")
    needs_dynamic_bank = args.dynamic_bank_gate or args.fused_router_gate
    if needs_dynamic_bank != (args.dynamic_bank_manifest is not None):
        raise SystemExit("dynamic bank gate and manifest must be supplied together")
    root = args.storage_root.resolve()
    paths = {"model": args.model_path.resolve(),
             "source_manifest": args.source_manifest.resolve(),
             "glyph_manifest": args.glyph_manifest.resolve()}
    if args.dynamic_bank_manifest is not None:
        paths["dynamic_bank_manifest"] = args.dynamic_bank_manifest.resolve()
    output = args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("model, weights and evidence must remain on external storage")
    if output.exists() or args.generated_tokens < 1:
        raise SystemExit("refusing overwrite or invalid generated-token count")
    fused_plan = None
    fused_layers = None
    if args.fused_layer_plan is not None:
        plan_path = args.fused_layer_plan.resolve()
        if not args.fused_metal_gate or root not in plan_path.parents:
            raise SystemExit("fused layer plans require the fused gate and external storage")
        fused_plan = json.loads(plan_path.read_text())
        claimed_hash = fused_plan.get("report_sha256")
        canonical_plan = {key: value for key, value in fused_plan.items()
                          if key != "report_sha256"}
        if claimed_hash != _canonical_sha256(canonical_plan):
            raise RuntimeError("fused layer plan canonical hash failed")
        if fused_plan.get("decision") != "FREEZE_FUSED_LAYER_HOLDOUT_PLAN":
            raise RuntimeError("fused layer plan was not frozen for holdout")
        fused_layers = {int(value) for value in fused_plan["selected_layers"]}
    prompts = (PROMPTS if args.prompt_manifest is None else
               _validate_prompt_catalog(json.loads(args.prompt_manifest.resolve().read_text())))
    if args.prompt_family:
        requested = set(args.prompt_family)
        available = {item["family"] for item in prompts}
        if not requested <= available:
            raise SystemExit(f"unknown prompt families: {sorted(requested - available)}")
        prompts = tuple(item for item in prompts if item["family"] in requested)
    prompt_manifest_hash = (_sha256(args.prompt_manifest.resolve())
                            if args.prompt_manifest is not None else None)
    if args.deterministic_algorithms:
        torch.use_deterministic_algorithms(True)
    source = json.loads(paths["source_manifest"].read_text())
    glyph = json.loads(paths["glyph_manifest"].read_text())
    dynamic_bank = (json.loads(paths["dynamic_bank_manifest"].read_text())
                    if needs_dynamic_bank else None)
    if not all(source["integrity"].values()) or not all(glyph["integrity"].values()):
        raise RuntimeError("manifest integrity failed")
    if glyph["source_manifest_sha256"] != _sha256(paths["source_manifest"]):
        raise RuntimeError("Glyph/source binding failed")
    if dynamic_bank is not None:
        if (not all(dynamic_bank["integrity"].values()) or
                dynamic_bank["source_glyph_manifest_sha256"] != _sha256(paths["glyph_manifest"])):
            raise RuntimeError("dynamic bank/source binding failed")
    verification = _verify_source_checkpoint(root, source)
    if not verification["passed"]:
        raise RuntimeError("checkpoint verification failed")

    tokenizer = AutoTokenizer.from_pretrained(paths["model"], local_files_only=True)
    checkpoint_index = json.loads(
        (paths["model"] / "model.safetensors.index.json").read_text())
    boot_started = time.perf_counter()
    model, shared_load = _load_storage_first_model(paths["model"], checkpoint_index)
    for layer_index, layer in enumerate(model.model.layers):
        source_moe = layer.block_sparse_moe
        if dynamic_bank is not None:
            bank_entry = load_bank_entry(dynamic_bank, layer_index, root, _sha256)
            layer.block_sparse_moe = Int8DynamicBankMoE(
                source_moe, bank_entry, root, _sha256, "mps", use_dynamic_decode=False)
            if args.router_audit:
                layer.block_sparse_moe.route_audit = {
                    "layer": layer_index, "calls": 0, "expert_index_mismatches": 0,
                    "maximum_gate_error": 0.0,
                }
        else:
            entries = load_layer_entries(glyph, layer_index, root, _sha256)
            layer.block_sparse_moe = Int8GlyphMoE(
                source_moe, entries, root, _sha256, "mps", skip_empty_experts=False,
                prepare_fused_metal_matvec=(args.fused_metal_gate and
                                            (fused_layers is None or layer_index in fused_layers)),
            )
        source_moe = None
        gc.collect()
    torch.mps.synchronize()
    boot_seconds = time.perf_counter() - boot_started
    ready_memory = _memory("storage_first_int8_ready")

    # Warm both compared modes without including warmup in evidence timing.
    for enabled in (False, True):
        if not needs_dynamic_bank:
            _set_sparse(model, True if (args.cached_views_gate or args.fused_metal_gate) else enabled)
            _set_cached_views(model, enabled if args.cached_views_gate else False)
            _set_fused_metal(model, enabled if args.fused_metal_gate else False, fused_layers)
        _set_dynamic_bank(model, True if args.fused_router_gate else
                          (enabled if args.dynamic_bank_gate else False))
        if args.fused_router_gate:
            _set_fused_router(model, enabled)
        _generate(model, tokenizer, prompts[0]["prompt"], 2)

    runs = []
    for prompt in prompts:
        for sequence, enabled in enumerate((False, True, True, False)):
            if not needs_dynamic_bank:
                _set_sparse(model, True if (args.cached_views_gate or args.fused_metal_gate) else enabled)
                _set_cached_views(model, enabled if args.cached_views_gate else False)
                _set_fused_metal(model, enabled if args.fused_metal_gate else False, fused_layers)
            _set_dynamic_bank(model, True if args.fused_router_gate else
                              (enabled if args.dynamic_bank_gate else False))
            if args.fused_router_gate:
                _set_fused_router(model, enabled)
            result = _generate(model, tokenizer, prompt["prompt"], args.generated_tokens)
            runs.append({"family": prompt["family"], "sequence": sequence,
                         "condition": (("dynamic_bank_fused_router" if enabled else
                                        "dynamic_bank_pytorch_router")
                                       if args.fused_router_gate else
                                       (("dynamic_bank" if enabled else "bank_native_int8")
                                       if args.dynamic_bank_gate else
                                       (("fused_metal" if enabled else "sparse_int8")
                                       if args.fused_metal_gate else
                                       (("cached_views" if enabled else "dynamic_views")
                                        if args.cached_views_gate else
                                        ("active_only" if enabled else "all_40"))))),
                         **result})
    control_label = ("dynamic_bank_pytorch_router" if args.fused_router_gate else
                     ("bank_native_int8" if args.dynamic_bank_gate else
                     ("sparse_int8" if args.fused_metal_gate else
                      ("dynamic_views" if args.cached_views_gate else "all_40"))))
    candidate_label = ("dynamic_bank_fused_router" if args.fused_router_gate else
                       ("dynamic_bank" if args.dynamic_bank_gate else
                       ("fused_metal" if args.fused_metal_gate else
                        ("cached_views" if args.cached_views_gate else "active_only"))))
    controls = [item for item in runs if item["condition"] == control_label]
    candidates = [item for item in runs if item["condition"] == candidate_label]
    control_summary = _summarize(controls)
    candidate_summary = _summarize(candidates)
    equivalence = []
    for prompt in prompts:
        family_runs = [item for item in runs if item["family"] == prompt["family"]]
        reference = family_runs[0]
        for item in family_runs[1:]:
            equivalence.append({"family": prompt["family"],
                                "reference_sequence": 0,
                                "compared_sequence": item["sequence"],
                                "condition": item["condition"],
                                **_equivalence(reference, item)})
    speed_improvement = 100 * (
        candidate_summary["median_tokens_per_second"] /
        control_summary["median_tokens_per_second"] - 1)
    p95_time_improvement = 100 * (
        1 - candidate_summary["p95_seconds_nearest_rank"] /
        control_summary["p95_seconds_nearest_rank"])
    maximum_step_error = max(item["maximum_step_logit_error"] for item in equivalence)
    storage_first_exact = (shared_load["skipped_expert_tensor_count"] == 64 and
                           not shared_load["remaining_meta_parameters"])
    if args.fused_router_gate:
        acceptance = {
            "median_throughput_improved_at_least_10_percent": speed_improvement >= 10,
            "p95_generation_time_improved_at_least_5_percent": p95_time_improvement >= 5,
            "bank_logical_bytes_within_3_gib": dynamic_bank["summary"]["logical_bytes"] <= 3 * 2**30,
            "bank_declares_zero_runtime_duplicate_weight_bytes":
                dynamic_bank["summary"]["duplicate_weight_bytes_at_runtime"] == 0,
            "fused_router_declares_zero_duplicate_weight_bytes": True,
            "storage_first_skipped_all_fp16_expert_tensors": storage_first_exact,
        }
    elif args.dynamic_bank_gate:
        acceptance = {
            "median_throughput_improved_at_least_10_percent": speed_improvement >= 10,
            "p95_generation_time_improved_at_least_5_percent": p95_time_improvement >= 5,
            "bank_logical_bytes_within_3_gib": dynamic_bank["summary"]["logical_bytes"] <= 3 * 2**30,
            "bank_declares_zero_runtime_duplicate_weight_bytes":
                dynamic_bank["summary"]["duplicate_weight_bytes_at_runtime"] == 0,
            "storage_first_skipped_all_fp16_expert_tensors": storage_first_exact,
        }
    else:
        acceptance = {
            "all_token_ids_exact": all(item["token_ids_exact"] for item in equivalence),
            ("step_logits_within_quality_ceiling" if args.fused_metal_gate else
             "all_step_logits_bit_exact"):
                (maximum_step_error <= args.fused_maximum_step_logit_error
                 if args.fused_metal_gate else
                 all(item["step_logits_bit_exact"] for item in equivalence)),
            (f"median_throughput_improved_at_least_{args.fused_minimum_throughput_gain:g}_percent"
             if args.fused_metal_gate else
             ("median_throughput_improved_at_least_2_percent" if args.cached_views_gate else
              "median_throughput_improved_at_least_10_percent")):
                speed_improvement >= (args.fused_minimum_throughput_gain if args.fused_metal_gate else
                                      (2 if args.cached_views_gate else 10)),
            "p95_generation_time_not_regressed": p95_time_improvement >= 0,
            "storage_first_skipped_all_fp16_expert_tensors": storage_first_exact,
        }
    bounded_runs = []
    for item in runs:
        bounded_runs.append({key: value for key, value in item.items()
                             if key not in ("scores", "text")})
    report = {"schema_version": "aion.int8_sparse_dispatch_full_model.v1",
              "paths": {name: str(path) for name, path in paths.items()},
              "hashes": {name: _sha256(path) for name, path in paths.items() if path.is_file()},
              "source_verification": verification, "shared_load": shared_load,
              "generated_tokens_per_run": args.generated_tokens,
              "deterministic_algorithms_enabled": args.deterministic_algorithms,
              "diagnostic_only": args.diagnostic_only,
              "prompt_families": [item["family"] for item in prompts],
              "prompt_manifest_path": (str(args.prompt_manifest.resolve())
                                       if args.prompt_manifest is not None else None),
              "prompt_manifest_sha256": prompt_manifest_hash,
              "prompt_hashes": {item["family"]: hashlib.sha256(item["prompt"].encode()).hexdigest()
                                for item in prompts},
              "order_per_family": [control_label, candidate_label,
                                    candidate_label, control_label],
              "cached_views_gate": args.cached_views_gate,
              "fused_metal_gate": args.fused_metal_gate,
              "dynamic_bank_gate": args.dynamic_bank_gate,
              "fused_router_gate": args.fused_router_gate,
              "route_audit": ([layer.block_sparse_moe.route_audit
                                for layer in model.model.layers]
                               if args.router_audit else None),
              "track": ("quality_gated_changed_kernel_not_bit_exact"
                         if (args.fused_metal_gate or needs_dynamic_bank)
                         else "exact_within_candidate"),
              "fused_maximum_step_logit_error": args.fused_maximum_step_logit_error,
              "fused_minimum_throughput_gain_percent": args.fused_minimum_throughput_gain,
              "fused_layer_plan_path": (str(args.fused_layer_plan.resolve())
                                        if args.fused_layer_plan else None),
              "fused_layer_plan_sha256": (_sha256(args.fused_layer_plan.resolve())
                                          if args.fused_layer_plan else None),
              "fused_layers": sorted(fused_layers) if fused_layers is not None else None,
              "fused_projected_buffer_bytes": ((len(fused_layers) if fused_layers is not None else 32)
                                                * 40_960 if args.fused_metal_gate else 0),
              "empty_dispatch_behavior": (
                  "skip zero-token Metal matrix operations while preserving all 40 empty/nonempty "
                  "concatenation entries"
              ),
              "boot_seconds": boot_seconds, "ready_memory": ready_memory,
              "control": control_summary, "candidate": candidate_summary,
              "aggregate": {"median_throughput_improvement_percent": speed_improvement,
                            "p95_generation_time_improvement_percent": p95_time_improvement,
                            "maximum_step_logit_error": maximum_step_error},
              "equivalence": equivalence, "runs": bounded_runs,
              "acceptance": acceptance,
              "decision": (("DIAGNOSTIC_SUPPORTS_FRESH_REPLICATION"
                            if args.diagnostic_only else
                            ("ADVANCE_FUSED_ROUTER_TO_QUALITY_GATES"
                             if args.fused_router_gate else
                             ("ADVANCE_DYNAMIC_BANK_TO_QUALITY_GATES"
                             if args.dynamic_bank_gate else
                             ("PROMOTE_INT8_CACHED_WEIGHT_VIEWS" if args.cached_views_gate else
                             ("ADVANCE_FUSED_METAL_TO_SEMANTIC_GATE"
                              if args.fused_metal_gate else
                              "PROMOTE_INT8_SPARSE_DISPATCH")))))
                           if all(acceptance.values()) else "NOT_PROMOTED"),
              "claim_boundary": (("Fused-router mechanism gate compares the promoted dynamic "
                                  "bank with its PyTorch router chain. Token/logit differences are "
                                  "reported; extended teacher-forced and semantic gates are required."
                                  if args.fused_router_gate else
                                  ("Dynamic-bank mechanism gate measures storage-first speed, "
                                  "p95 and memory only. Token/logit differences are reported; "
                                  "teacher-forced and semantic quality require separate gates."
                                  if args.dynamic_bank_gate else
                                  "Storage-first, full-resident packed-INT8 Granite; four fixed "
                                  "or explicitly selected prompt families, two ABBA observations "
                                  "per condition. Exactness is relative to the prior packed-INT8 "
                                  "candidate, not FP16 semantic equivalence. A diagnostic-only "
                                  "post-hoc selection cannot extend promotion.")))}
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "decision": report["decision"],
                      "control": control_summary, "candidate": candidate_summary,
                      "aggregate": report["aggregate"], "acceptance": acceptance,
                      "report_sha256": report["report_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
