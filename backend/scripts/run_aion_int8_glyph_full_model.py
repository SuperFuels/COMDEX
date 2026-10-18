#!/usr/bin/env python3
"""Run the first full-model quality/performance gate for native INT8 Glyph experts."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import statistics
import time
from typing import Any

import psutil
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from backend.modules.aion_inference.int8_glyph_moe import Int8GlyphMoE, load_layer_entries
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256
from backend.scripts.run_aion_storage_first_multiprompt import PROMPTS, _generate


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def _memory(label: str) -> dict[str, int | str]:
    return {"label": label,
            "mps_current_allocated_bytes": torch.mps.current_allocated_memory(),
            "mps_driver_allocated_bytes": torch.mps.driver_allocated_memory(),
            "process_rss_bytes": psutil.Process().memory_info().rss,
            "system_available_bytes": psutil.virtual_memory().available}


def _summarize(results: list[dict[str, Any]]) -> dict[str, float]:
    throughputs = [len(result["token_ids"]) / result["seconds"] for result in results]
    ttft = [result["time_to_first_token_seconds"] for result in results]
    return {"total_seconds": sum(result["seconds"] for result in results),
            "median_tokens_per_second": statistics.median(throughputs),
            "minimum_tokens_per_second": min(throughputs),
            "maximum_tokens_per_second": max(throughputs),
            "median_time_to_first_token_seconds": statistics.median(ttft)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--glyph-manifest", type=Path, required=True)
    parser.add_argument("--generated-tokens", type=int, default=8)
    parser.add_argument("--retain-fp16-layer", type=int, action="append", default=[])
    parser.add_argument("--minimum-throughput-improvement-percent", type=float, default=10.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"model": args.model_path.resolve(),
             "source_manifest": args.source_manifest.resolve(),
             "glyph_manifest": args.glyph_manifest.resolve()}
    output = args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all model inputs and evidence must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    if not torch.backends.mps.is_available() or args.generated_tokens < 1:
        raise SystemExit("valid token count and Apple Metal/MPS are required")
    retained_fp16_layers = sorted(set(args.retain_fp16_layer))
    if any(layer < 0 or layer >= 32 for layer in retained_fp16_layers):
        raise SystemExit("retained FP16 layers must be between 0 and 31")

    source_manifest = json.loads(paths["source_manifest"].read_text())
    glyph_manifest = json.loads(paths["glyph_manifest"].read_text())
    if not all(source_manifest["integrity"].values()) or not all(glyph_manifest["integrity"].values()):
        raise RuntimeError("source or Glyph manifest integrity gate failed")
    if glyph_manifest["source_manifest_sha256"] != _sha256(paths["source_manifest"]):
        raise RuntimeError("Glyph library is not bound to supplied source manifest")
    checkpoint_verification = []
    for entry in source_manifest["source_checkpoint"]:
        checkpoint = Path(entry["path"]).resolve()
        actual = _sha256(checkpoint)
        checkpoint_verification.append({"path": str(checkpoint), "expected": entry["sha256"],
                                        "actual": actual, "passed": actual == entry["sha256"]})
    if not all(item["passed"] for item in checkpoint_verification):
        raise RuntimeError("source checkpoint verification failed")

    tokenizer = AutoTokenizer.from_pretrained(paths["model"], local_files_only=True)
    memory = [_memory("before_model_load")]
    load_started = time.perf_counter()
    model = AutoModelForCausalLM.from_pretrained(
        paths["model"], local_files_only=True, dtype=torch.float16,
        device_map={"": "mps"}, low_cpu_mem_usage=True,
    ).eval()
    torch.mps.synchronize()
    model_load_seconds = time.perf_counter() - load_started
    memory.append(_memory("fp16_model_loaded"))

    selected = [dict(item) for item in PROMPTS]
    controls = [_generate(model, tokenizer, item["prompt"], args.generated_tokens)
                for item in selected]
    memory.append(_memory("after_fp16_control"))

    install_started = time.perf_counter()
    installed_layers = 0
    for layer_index, layer in enumerate(model.model.layers):
        if layer_index in retained_fp16_layers:
            continue
        source_moe = layer.block_sparse_moe
        entries = load_layer_entries(glyph_manifest, layer_index, root, _sha256)
        replacement = Int8GlyphMoE(source_moe, entries, root, _sha256, "mps")
        layer.block_sparse_moe = replacement
        source_moe = None
        installed_layers += 1
        gc.collect()
        torch.mps.empty_cache()
        if layer_index in (7, 15, 23, 31):
            memory.append(_memory(f"int8_layers_installed_{layer_index + 1}"))
    torch.mps.synchronize()
    install_seconds = time.perf_counter() - install_started
    memory.append(_memory("int8_model_ready"))

    candidates = [_generate(model, tokenizer, item["prompt"], args.generated_tokens)
                  for item in selected]
    memory.append(_memory("after_int8_candidate"))
    comparisons = []
    total_token_matches = 0
    total_tokens = 0
    for prompt, control, candidate in zip(selected, controls, candidates, strict=True):
        errors = [float((left - right).abs().max().item()) for left, right in zip(
            control["scores"], candidate["scores"], strict=True,
        )]
        token_matches = sum(left == right for left, right in zip(
            control["token_ids"], candidate["token_ids"], strict=True,
        ))
        total_token_matches += token_matches
        total_tokens += len(control["token_ids"])
        comparisons.append({
            "family": prompt["family"],
            "prompt_sha256": hashlib.sha256(prompt["prompt"].encode()).hexdigest(),
            "token_matches": token_matches, "token_count": len(control["token_ids"]),
            "token_agreement_fraction": token_matches / len(control["token_ids"]),
            "control_token_ids": control["token_ids"],
            "candidate_token_ids": candidate["token_ids"],
            "maximum_step_logit_error": max(errors, default=0.0),
            "mean_maximum_step_logit_error": statistics.mean(errors) if errors else 0.0,
            "candidate_all_logits_finite": all(bool(torch.isfinite(score).all())
                                                for score in candidate["scores"]),
        })
    control_summary = _summarize(controls)
    candidate_summary = _summarize(candidates)
    throughput_improvement = 100 * (
        candidate_summary["median_tokens_per_second"] /
        control_summary["median_tokens_per_second"] - 1
    )
    token_agreement = total_token_matches / total_tokens
    hybrid_expert_bytes = int(glyph_manifest["summary"]["logical_packed_bytes"])
    for layer_index in retained_fp16_layers:
        layer_entry = glyph_manifest["layers"][layer_index]
        index_document = json.loads(Path(layer_entry["index_path"]).read_text())
        hybrid_expert_bytes -= int(layer_entry["logical_packed_bytes"])
        hybrid_expert_bytes += sum(int(item["source_bytes"])
                                   for item in index_document["experts"])
    acceptance = {
        "all_32_layers_have_declared_precision": (
            installed_layers + len(retained_fp16_layers) == 32
        ),
        "all_candidate_logits_finite": all(x["candidate_all_logits_finite"] for x in comparisons),
        "aggregate_token_agreement_at_least_75_percent": token_agreement >= 0.75,
        "throughput_passed_declared_gate": (
            throughput_improvement >= args.minimum_throughput_improvement_percent
        ),
        "hybrid_expert_library_within_3_gib": hybrid_expert_bytes <= 3 * 1024**3,
    }
    for result in (*controls, *candidates):
        result.pop("scores")
        result.pop("text")
    report = {
        "schema_version": "aion.int8_glyph_full_model.v1",
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": {"source_manifest": _sha256(paths["source_manifest"]),
                   "glyph_manifest": _sha256(paths["glyph_manifest"])},
        "checkpoint_verification": checkpoint_verification,
        "generated_tokens_per_prompt": args.generated_tokens,
        "retained_fp16_layers": retained_fp16_layers,
        "int8_layer_count": installed_layers,
        "hybrid_expert_bytes": hybrid_expert_bytes,
        "hybrid_expert_gibibytes": hybrid_expert_bytes / 1024**3,
        "minimum_throughput_improvement_percent": args.minimum_throughput_improvement_percent,
        "prompt_count": len(selected), "model_load_seconds": model_load_seconds,
        "int8_install_seconds": install_seconds, "memory": memory,
        "control": control_summary, "candidate": candidate_summary,
        "aggregate": {"token_agreement_fraction": token_agreement,
                      "median_throughput_improvement_percent": throughput_improvement,
                      "time_to_first_token_change_percent": 100 * (
                          candidate_summary["median_time_to_first_token_seconds"] /
                          control_summary["median_time_to_first_token_seconds"] - 1)},
        "comparisons": comparisons, "acceptance": acceptance,
        "decision": "ADVANCE_TO_BLINDED_QUALITY_GATE" if all(acceptance.values())
                    else "NOT_PROMOTED",
        "claim_boundary": (
            "First full-resident four-prompt, eight-token mechanism gate for lossy INT8 "
            "Granite experts on Metal. It is not exact, not storage-first generation, and "
            "does not establish long-generation or task-level quality."
        ),
    }
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
