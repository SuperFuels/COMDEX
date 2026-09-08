#!/usr/bin/env python3
"""Compare dynamic-bank INT8 directly with FP16 on identical forced histories."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from backend.modules.aion_inference.int8_dynamic_bank_moe import (
    Int8DynamicBankMoE, load_bank_entry,
)
from backend.scripts.run_aion_int8_glyph_full_model import _canonical_sha256
from backend.scripts.run_aion_moe_end_to_end_fault_in import _chat_tokens, _sha256
from backend.scripts.run_aion_storage_first_multiprompt import PROMPTS
from backend.scripts.run_forced_int8_quality import _quality_metrics


@torch.inference_mode()
def _incremental_logits(model, encoded, continuation: list[int]):
    started = time.perf_counter()
    output = model(**encoded, use_cache=True)
    logits = [output.logits[0, -1].detach().float().cpu()]
    past = output.past_key_values
    for token in continuation[:-1]:
        token_tensor = torch.tensor([[token]], dtype=torch.long, device="mps")
        output = model(input_ids=token_tensor, past_key_values=past, use_cache=True)
        logits.append(output.logits[0, -1].detach().float().cpu())
        past = output.past_key_values
    torch.mps.synchronize()
    return torch.stack(logits), time.perf_counter() - started


def _aggregate(comparisons):
    positions = sum(item["positions"] for item in comparisons)
    return {
        "positions": positions,
        "teacher_forced_top1_agreement_fraction":
            sum(item["top1_agreement_count"] for item in comparisons) / positions,
        "mean_top5_overlap_fraction":
            sum(item["mean_top5_overlap_fraction"] * item["positions"]
                for item in comparisons) / positions,
        "mean_kl_divergence_nats":
            sum(item["mean_kl_divergence_nats"] * item["positions"]
                for item in comparisons) / positions,
        "mean_control_token_nll_delta_nats":
            sum(item["mean_control_token_nll_delta_nats"] * item["positions"]
                for item in comparisons) / positions,
        "total_seconds": sum(item["candidate_seconds"] for item in comparisons),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--bank-manifest", type=Path, required=True)
    parser.add_argument("--generation-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"model": args.model_path.resolve(), "bank_manifest": args.bank_manifest.resolve(),
             "generation_evidence": args.generation_evidence.resolve()}
    output_path = args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(), output_path)):
        raise SystemExit("model, banks and evidence must remain on external storage")
    if output_path.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output_path}")
    bank = json.loads(paths["bank_manifest"].read_text())
    generation = json.loads(paths["generation_evidence"].read_text())
    if not all(bank["integrity"].values()):
        raise RuntimeError("bank manifest integrity failed")
    by_family = {item["family"]: item for item in generation["comparisons"]}
    tokenizer = AutoTokenizer.from_pretrained(paths["model"], local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        paths["model"], local_files_only=True, dtype=torch.float16,
        device_map={"": "mps"}, low_cpu_mem_usage=True,
    ).eval()
    encoded = {item["family"]: _chat_tokens(tokenizer, item["prompt"]) for item in PROMPTS}
    fp16_logits = {}; fp16_seconds = {}
    for prompt in PROMPTS:
        family = prompt["family"]
        fp16_logits[family], fp16_seconds[family] = _incremental_logits(
            model, encoded[family], by_family[family]["control_token_ids"])
    for layer_index, layer in enumerate(model.model.layers):
        source_moe = layer.block_sparse_moe
        entry = load_bank_entry(bank, layer_index, root, _sha256)
        layer.block_sparse_moe = Int8DynamicBankMoE(
            source_moe, entry, root, _sha256, "mps", use_dynamic_decode=False)
        source_moe = None
        gc.collect()
    torch.mps.synchronize()
    native_logits = {}; native_seconds = {}
    dynamic_logits = {}; dynamic_seconds = {}
    for prompt in PROMPTS:
        family = prompt["family"]
        continuation = by_family[family]["control_token_ids"]
        native_logits[family], native_seconds[family] = _incremental_logits(
            model, encoded[family], continuation)
    for layer in model.model.layers:
        layer.block_sparse_moe.use_dynamic_decode = True
    for prompt in PROMPTS:
        family = prompt["family"]
        continuation = by_family[family]["control_token_ids"]
        dynamic_logits[family], dynamic_seconds[family] = _incremental_logits(
            model, encoded[family], continuation)
    native_comparisons = []; dynamic_comparisons = []
    for prompt in PROMPTS:
        family = prompt["family"]
        continuation = by_family[family]["control_token_ids"]
        common = {"family": family,
                  "prompt_sha256": hashlib.sha256(prompt["prompt"].encode()).hexdigest(),
                  "control_seconds": fp16_seconds[family]}
        native_comparisons.append({**common, "candidate_seconds": native_seconds[family],
                                   **_quality_metrics(fp16_logits[family], native_logits[family],
                                                      continuation)})
        dynamic_comparisons.append({**common, "candidate_seconds": dynamic_seconds[family],
                                    **_quality_metrics(fp16_logits[family], dynamic_logits[family],
                                                       continuation)})
    native_aggregate = _aggregate(native_comparisons)
    dynamic_aggregate = _aggregate(dynamic_comparisons)
    speed_gain = 100 * (1 - dynamic_aggregate["total_seconds"] /
                        native_aggregate["total_seconds"])
    acceptance = {
        "dynamic_top1_within_1pp_of_native":
            dynamic_aggregate["teacher_forced_top1_agreement_fraction"] >=
            native_aggregate["teacher_forced_top1_agreement_fraction"] - 0.01,
        "dynamic_top5_within_1pp_of_native":
            dynamic_aggregate["mean_top5_overlap_fraction"] >=
            native_aggregate["mean_top5_overlap_fraction"] - 0.01,
        "dynamic_kl_no_more_than_0_002_above_native":
            dynamic_aggregate["mean_kl_divergence_nats"] <=
            native_aggregate["mean_kl_divergence_nats"] + 0.002,
        "dynamic_nll_no_more_than_0_02_above_native":
            dynamic_aggregate["mean_control_token_nll_delta_nats"] <=
            native_aggregate["mean_control_token_nll_delta_nats"] + 0.02,
        "incremental_teacher_time_improved_at_least_25_percent": speed_gain >= 25,
    }
    report = {"schema_version": "aion.dynamic_bank_teacher_quality.v1",
              "track": "quality_gated_changed_kernel_not_bit_exact",
              "paths": {name: str(path) for name, path in paths.items()},
              "hashes": {name: _sha256(path) for name, path in paths.items() if path.is_file()},
              "families": [item["family"] for item in PROMPTS],
              "forced_positions": native_aggregate["positions"],
              "native_comparisons": native_comparisons,
              "dynamic_comparisons": dynamic_comparisons,
              "native_aggregate": native_aggregate,
              "dynamic_aggregate": dynamic_aggregate,
              "dynamic_vs_native_teacher_time_improvement_percent": speed_gain,
              "acceptance": acceptance,
              "decision": ("ADVANCE_DYNAMIC_BANK_TO_FROZEN_SEMANTIC_GATE"
                           if all(acceptance.values()) else "STOP_DYNAMIC_BANK_QUALITY"),
              "claim_boundary": ("Incremental teacher forcing on 256 FP16-generated positions "
                                 "from four frozen families. This measures probability preservation "
                                 "and speed but not absolute semantic task competence.")}
    report["report_sha256"] = _canonical_sha256(report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output_path), "decision": report["decision"],
                      "native": native_aggregate, "dynamic": dynamic_aggregate,
                      "speed_improvement_percent": speed_gain,
                      "acceptance": acceptance, "report_sha256": report["report_sha256"]},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
