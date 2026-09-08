#!/usr/bin/env python3
"""Frozen semantic-preservation gate for native and dynamic-bank INT8."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path

import torch
from transformers import AutoTokenizer

from backend.modules.aion_inference.int8_dynamic_bank_moe import (
    Int8DynamicBankMoE, load_bank_entry,
)
from backend.scripts.run_aion_int8_glyph_full_model import _canonical_sha256
from backend.scripts.run_aion_int8_semantic_mcq_gate import _run
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256
from backend.scripts.run_aion_storage_first_boot import _load_storage_first_model


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--bank-manifest", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"model": args.model_path.resolve(), "bank_manifest": args.bank_manifest.resolve(),
             "tasks": args.tasks.resolve()}
    output_path = args.output.resolve()
    if root not in paths["model"].parents or root not in paths["bank_manifest"].parents:
        raise SystemExit("model artifacts must remain on external storage")
    if output_path.exists() or root not in output_path.parents:
        raise SystemExit("evidence must be new and on external storage")
    cases = json.loads(paths["tasks"].read_text())["cases"]
    bank = json.loads(paths["bank_manifest"].read_text())
    if not all(bank["integrity"].values()):
        raise RuntimeError("bank manifest integrity failed")
    tokenizer = AutoTokenizer.from_pretrained(paths["model"], local_files_only=True)
    checkpoint_index = json.loads(
        (paths["model"] / "model.safetensors.index.json").read_text())
    model, shared_load = _load_storage_first_model(paths["model"], checkpoint_index)
    for layer_index, layer in enumerate(model.model.layers):
        source_moe = layer.block_sparse_moe
        entry = load_bank_entry(bank, layer_index, root, _sha256)
        layer.block_sparse_moe = Int8DynamicBankMoE(
            source_moe, entry, root, _sha256, "mps", use_dynamic_decode=False)
        source_moe = None
        gc.collect()
    torch.mps.synchronize()
    native = _run(model, tokenizer, cases)
    for layer in model.model.layers:
        layer.block_sparse_moe.use_dynamic_decode = True
    dynamic = _run(model, tokenizer, cases)
    native_passes = sum(item["passed"] for item in native)
    dynamic_passes = sum(item["passed"] for item in dynamic)
    answer_matches = sum(left["observed"] == right["observed"]
                         for left, right in zip(native, dynamic, strict=True))
    native_tps = sum(item["token_count"] for item in native) / sum(item["seconds"] for item in native)
    dynamic_tps = sum(item["token_count"] for item in dynamic) / sum(item["seconds"] for item in dynamic)
    speed_gain = 100 * (dynamic_tps / native_tps - 1)
    comparisons = [{"id": left["id"], "family": left["family"], "expected": left["expected"],
                    "native_observed": left["observed"], "dynamic_observed": right["observed"],
                    "native_passed": left["passed"], "dynamic_passed": right["passed"]}
                   for left, right in zip(native, dynamic, strict=True)]
    acceptance = {"dynamic_lost_no_more_than_one_native_pass":
                      dynamic_passes >= native_passes - 1,
                  "answer_agreement_at_least_90_percent": answer_matches / len(cases) >= 0.90,
                  "dynamic_answers_all_parseable": all(item["observed"] is not None for item in dynamic),
                  "throughput_improved_at_least_25_percent": speed_gain >= 25,
                  "storage_first_skipped_all_fp16_experts":
                      shared_load["skipped_expert_tensor_count"] == 64}
    report = {"schema_version": "aion.dynamic_bank_semantic_preservation.v1",
              "track": "quality_gated_changed_kernel_not_bit_exact",
              "paths": {name: str(path) for name, path in paths.items()},
              "hashes": {name: _sha256(path) for name, path in paths.items() if path.is_file()},
              "native": {"passes": native_passes, "tokens_per_second": native_tps},
              "dynamic": {"passes": dynamic_passes, "tokens_per_second": dynamic_tps},
              "answer_agreement_fraction": answer_matches / len(cases),
              "throughput_improvement_percent": speed_gain,
              "comparisons": comparisons, "acceptance": acceptance,
              "decision": ("PROMOTE_DYNAMIC_BANK_WITHIN_VALIDATED_BOUNDARY"
                           if all(acceptance.values()) else "NOT_PROMOTED"),
              "claim_boundary": ("Twelve previously frozen synthetic MCQ tasks plus prior "
                                 "teacher-forced and four-family generation gates. This establishes "
                                 "relative preservation, not broad absolute model competence.")}
    report["report_sha256"] = _canonical_sha256(report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output_path), "decision": report["decision"],
                      "native": report["native"], "dynamic": report["dynamic"],
                      "answer_agreement_fraction": report["answer_agreement_fraction"],
                      "throughput_improvement_percent": speed_gain,
                      "acceptance": acceptance, "report_sha256": report["report_sha256"]},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
