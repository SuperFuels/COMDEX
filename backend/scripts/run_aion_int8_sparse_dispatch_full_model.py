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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"model": args.model_path.resolve(),
             "source_manifest": args.source_manifest.resolve(),
             "glyph_manifest": args.glyph_manifest.resolve()}
    output = args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("model, weights and evidence must remain on external storage")
    if output.exists() or args.generated_tokens < 1:
        raise SystemExit("refusing overwrite or invalid generated-token count")
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
    if not all(source["integrity"].values()) or not all(glyph["integrity"].values()):
        raise RuntimeError("manifest integrity failed")
    if glyph["source_manifest_sha256"] != _sha256(paths["source_manifest"]):
        raise RuntimeError("Glyph/source binding failed")
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
        entries = load_layer_entries(glyph, layer_index, root, _sha256)
        layer.block_sparse_moe = Int8GlyphMoE(
            source_moe, entries, root, _sha256, "mps", skip_empty_experts=False,
        )
        source_moe = None
        gc.collect()
    torch.mps.synchronize()
    boot_seconds = time.perf_counter() - boot_started
    ready_memory = _memory("storage_first_int8_ready")

    # Warm both dispatch modes without including warmup in evidence timing.
    for enabled in (False, True):
        _set_sparse(model, enabled)
        _generate(model, tokenizer, prompts[0]["prompt"], 2)

    runs = []
    for prompt in prompts:
        for sequence, enabled in enumerate((False, True, True, False)):
            _set_sparse(model, enabled)
            result = _generate(model, tokenizer, prompt["prompt"], args.generated_tokens)
            runs.append({"family": prompt["family"], "sequence": sequence,
                         "condition": "active_only" if enabled else "all_40",
                         **result})
    controls = [item for item in runs if item["condition"] == "all_40"]
    candidates = [item for item in runs if item["condition"] == "active_only"]
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
    acceptance = {
        "all_token_ids_exact": all(item["token_ids_exact"] for item in equivalence),
        "all_step_logits_bit_exact": all(item["step_logits_bit_exact"] for item in equivalence),
        "median_throughput_improved_at_least_10_percent": speed_improvement >= 10,
        "p95_generation_time_not_regressed": p95_time_improvement >= 0,
        "storage_first_skipped_all_fp16_expert_tensors": (
            shared_load["skipped_expert_tensor_count"] == 64 and
            not shared_load["remaining_meta_parameters"]),
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
              "order_per_family": ["all_40", "active_only", "active_only", "all_40"],
              "empty_dispatch_behavior": (
                  "skip zero-token Metal matrix operations while preserving all 40 empty/nonempty "
                  "concatenation entries"
              ),
              "boot_seconds": boot_seconds, "ready_memory": ready_memory,
              "control": control_summary, "candidate": candidate_summary,
              "aggregate": {"median_throughput_improvement_percent": speed_improvement,
                            "p95_generation_time_improvement_percent": p95_time_improvement,
                            "maximum_step_logit_error": max(
                                item["maximum_step_logit_error"] for item in equivalence)},
              "equivalence": equivalence, "runs": bounded_runs,
              "acceptance": acceptance,
              "decision": (("DIAGNOSTIC_SUPPORTS_FRESH_REPLICATION"
                            if args.diagnostic_only else "PROMOTE_INT8_SPARSE_DISPATCH")
                           if all(acceptance.values()) else "NOT_PROMOTED"),
              "claim_boundary": ("Storage-first, full-resident packed-INT8 Granite; four fixed "
                                 "or explicitly selected prompt families, two ABBA observations "
                                 "per condition. Exactness is relative to the prior packed-INT8 "
                                 "candidate, not FP16 semantic equivalence. A diagnostic-only "
                                 "post-hoc selection cannot extend promotion.")}
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
