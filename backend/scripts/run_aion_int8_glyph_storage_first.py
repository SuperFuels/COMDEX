#!/usr/bin/env python3
"""Boot Granite directly from INT8 Glyph experts without materializing FP16 experts."""

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
from backend.scripts.run_aion_int8_glyph_full_model import _canonical_sha256, _memory, _summarize
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256
from backend.scripts.run_aion_storage_first_boot import (
    _load_storage_first_model, _verify_source_checkpoint,
)
from backend.scripts.run_aion_storage_first_multiprompt import PROMPTS, _generate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--glyph-manifest", type=Path, required=True)
    parser.add_argument("--control-evidence", type=Path, required=True)
    parser.add_argument("--generated-tokens", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"model": args.model_path.resolve(),
             "source_manifest": args.source_manifest.resolve(),
             "glyph_manifest": args.glyph_manifest.resolve(),
             "control_evidence": args.control_evidence.resolve()}
    output = args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all model inputs and evidence must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    if not torch.backends.mps.is_available() or args.generated_tokens < 1:
        raise SystemExit("valid token count and Apple Metal/MPS are required")

    source = json.loads(paths["source_manifest"].read_text())
    glyph = json.loads(paths["glyph_manifest"].read_text())
    control = json.loads(paths["control_evidence"].read_text())
    if not all(source["integrity"].values()) or not all(glyph["integrity"].values()):
        raise RuntimeError("manifest integrity failed")
    if glyph["source_manifest_sha256"] != _sha256(paths["source_manifest"]):
        raise RuntimeError("Glyph/source binding failed")
    if control["generated_tokens_per_prompt"] != args.generated_tokens:
        raise RuntimeError("control token count mismatch")
    verification = _verify_source_checkpoint(root, source)
    if not verification["passed"]:
        raise RuntimeError("source checkpoint verification failed")

    checkpoint_index_path = paths["model"] / "model.safetensors.index.json"
    checkpoint_index = json.loads(checkpoint_index_path.read_text())
    tokenizer = AutoTokenizer.from_pretrained(paths["model"], local_files_only=True)
    memory = [_memory("before_storage_first_boot")]
    boot_started = time.perf_counter()
    model, shared_load = _load_storage_first_model(paths["model"], checkpoint_index)
    memory.append(_memory("shared_weights_loaded_without_fp16_experts"))
    install_started = time.perf_counter()
    for layer_index, layer in enumerate(model.model.layers):
        source_moe = layer.block_sparse_moe
        entries = load_layer_entries(glyph, layer_index, root, _sha256)
        layer.block_sparse_moe = Int8GlyphMoE(source_moe, entries, root, _sha256, "mps")
        source_moe = None
        gc.collect()
        if layer_index in (7, 15, 23, 31):
            memory.append(_memory(f"glyph_layers_loaded_{layer_index + 1}"))
    torch.mps.synchronize()
    install_seconds = time.perf_counter() - install_started
    total_boot_seconds = time.perf_counter() - boot_started
    memory.append(_memory("storage_first_int8_ready"))

    selected = [dict(item) for item in PROMPTS]
    results = [_generate(model, tokenizer, item["prompt"], args.generated_tokens)
               for item in selected]
    summary = _summarize(results)
    memory.append(_memory("after_generation"))
    comparisons = []
    matches = 0
    tokens = 0
    control_by_family = {item["family"]: item for item in control["comparisons"]}
    for prompt, result in zip(selected, results, strict=True):
        expected = control_by_family[prompt["family"]]["control_token_ids"]
        count = sum(left == right for left, right in zip(expected, result["token_ids"], strict=True))
        matches += count
        tokens += len(expected)
        comparisons.append({"family": prompt["family"], "matches": count,
                            "tokens": len(expected), "token_ids": result["token_ids"],
                            "prompt_sha256": hashlib.sha256(prompt["prompt"].encode()).hexdigest()})
        result.pop("scores")
        result.pop("text")
    token_agreement = matches / tokens
    fp16_ready = next(item for item in control["memory"] if item["label"] == "fp16_model_loaded")
    int8_ready = next(item for item in memory if item["label"] == "storage_first_int8_ready")
    memory_reduction = 100 * (1 - int8_ready["mps_current_allocated_bytes"] /
                              fp16_ready["mps_current_allocated_bytes"])
    boot_improvement = 100 * (1 - total_boot_seconds / control["model_load_seconds"])
    control_tps = control["control"]["median_tokens_per_second"]
    throughput_change = 100 * (summary["median_tokens_per_second"] / control_tps - 1)
    acceptance = {
        "no_fp16_expert_parameters_materialized": (
            shared_load["skipped_expert_tensor_count"] == 64 and
            not shared_load["remaining_meta_parameters"]
        ),
        "token_agreement_is_100_percent": token_agreement == 1.0,
        "active_mps_memory_reduced_at_least_40_percent": memory_reduction >= 40,
        "boot_improved_at_least_20_percent": boot_improvement >= 20,
        "throughput_not_regressed_more_than_5_percent": throughput_change >= -5,
    }
    report = {
        "schema_version": "aion.int8_glyph_storage_first.v1",
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": {name: _sha256(path) for name, path in paths.items() if path.is_file()},
        "source_verification": verification, "shared_load": shared_load,
        "glyph_install_seconds": install_seconds, "total_boot_seconds": total_boot_seconds,
        "generated_tokens_per_prompt": args.generated_tokens,
        "memory": memory, "candidate": summary, "comparisons": comparisons,
        "aggregate": {"token_agreement_fraction": token_agreement,
                      "active_mps_memory_reduction_percent_vs_fp16": memory_reduction,
                      "boot_time_improvement_percent_vs_full_fp16_load": boot_improvement,
                      "median_throughput_change_percent_vs_fp16_control": throughput_change},
        "acceptance": acceptance,
        "decision": "ADVANCE_TO_LONG_QUALITY_GATE" if all(acceptance.values())
                    else "NOT_PROMOTED",
        "claim_boundary": (
            "Storage-first full-resident INT8 mechanism test compared with immediately prior "
            "hash-bound FP16 evidence, not contemporaneous ABBA. Four prompts and eight tokens "
            "do not establish long-generation or semantic quality."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "decision": report["decision"],
                      "candidate": summary, "aggregate": report["aggregate"],
                      "acceptance": acceptance, "report_sha256": report["report_sha256"]},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
