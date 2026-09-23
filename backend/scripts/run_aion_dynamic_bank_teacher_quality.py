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
    PRECISE_ROUTER_PYTORCH_FALLBACK_LAYERS,
    PRECISE_ROUTER_UNGUARDED_DECODE_TOKENS,
    PROJECTION_PIPELINE_INITIAL_DECODE_TOKENS,
    Int8DynamicBankMoE,
    load_bank_entry,
)
from backend.scripts.run_aion_int8_glyph_full_model import _canonical_sha256
from backend.scripts.run_aion_moe_end_to_end_fault_in import _chat_tokens, _sha256
from backend.scripts.run_aion_storage_first_multiprompt import PROMPTS
from backend.scripts.run_aion_storage_first_multiprompt import _validate_prompt_catalog
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


def _control_continuations(generation: dict, families: list[str]) -> dict[str, list[int]]:
    if "comparisons" in generation:
        by_family = {item["family"]: item["control_token_ids"]
                     for item in generation["comparisons"]}
    elif "runs" in generation:
        opening_controls = [item for item in generation["runs"]
                            if item.get("sequence") == 0]
        by_family = {item["family"]: item["token_ids"] for item in opening_controls}
    else:
        raise ValueError("generation evidence has no supported continuation records")
    missing = sorted(set(families) - set(by_family))
    if missing:
        raise ValueError(f"generation evidence is missing families: {missing}")
    return {family: by_family[family] for family in families}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--bank-manifest", type=Path, required=True)
    parser.add_argument("--generation-evidence", type=Path, required=True)
    parser.add_argument("--prompt-manifest", type=Path)
    parser.add_argument("--fused-router-gate", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"model": args.model_path.resolve(), "bank_manifest": args.bank_manifest.resolve(),
             "generation_evidence": args.generation_evidence.resolve()}
    prompt_manifest = args.prompt_manifest.resolve() if args.prompt_manifest is not None else None
    output_path = args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(), output_path)):
        raise SystemExit("model, banks and evidence must remain on external storage")
    if output_path.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output_path}")
    bank = json.loads(paths["bank_manifest"].read_text())
    generation = json.loads(paths["generation_evidence"].read_text())
    if not all(bank["integrity"].values()):
        raise RuntimeError("bank manifest integrity failed")
    prompts = (PROMPTS if prompt_manifest is None else
               _validate_prompt_catalog(json.loads(prompt_manifest.read_text())))
    families = [item["family"] for item in prompts]
    continuations = _control_continuations(generation, families)
    tokenizer = AutoTokenizer.from_pretrained(paths["model"], local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        paths["model"], local_files_only=True, dtype=torch.float16,
        device_map={"": "mps"}, low_cpu_mem_usage=True,
    ).eval()
    encoded = {item["family"]: _chat_tokens(tokenizer, item["prompt"]) for item in prompts}
    fp16_logits = {}; fp16_seconds = {}
    for prompt in prompts:
        family = prompt["family"]
        fp16_logits[family], fp16_seconds[family] = _incremental_logits(
            model, encoded[family], continuations[family])
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
    for prompt in prompts:
        family = prompt["family"]
        continuation = continuations[family]
        native_logits[family], native_seconds[family] = _incremental_logits(
            model, encoded[family], continuation)
    for layer in model.model.layers:
        layer.block_sparse_moe.use_dynamic_decode = True
    for prompt in prompts:
        family = prompt["family"]
        continuation = continuations[family]
        dynamic_logits[family], dynamic_seconds[family] = _incremental_logits(
            model, encoded[family], continuation)
    fused_logits = {}; fused_seconds = {}
    if args.fused_router_gate:
        for index, layer in enumerate(model.model.layers):
            layer.block_sparse_moe.use_fused_router = True
            layer.block_sparse_moe.router_fallback_after_tokens = (
                PRECISE_ROUTER_UNGUARDED_DECODE_TOKENS
                if index in PRECISE_ROUTER_PYTORCH_FALLBACK_LAYERS else None)
            layer.block_sparse_moe.use_fused_prefill_router = True
            layer.block_sparse_moe.use_fused_projection_pipeline = True
            layer.block_sparse_moe.projection_pipeline_decode_tokens = (
                PROJECTION_PIPELINE_INITIAL_DECODE_TOKENS)
        for prompt in prompts:
            family = prompt["family"]
            continuation = continuations[family]
            fused_logits[family], fused_seconds[family] = _incremental_logits(
                model, encoded[family], continuation)
    native_comparisons = []; dynamic_comparisons = []
    for prompt in prompts:
        family = prompt["family"]
        continuation = continuations[family]
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
    fused_comparisons = []
    if args.fused_router_gate:
        for prompt in prompts:
            family = prompt["family"]
            continuation = continuations[family]
            common = {"family": family,
                      "prompt_sha256": hashlib.sha256(prompt["prompt"].encode()).hexdigest(),
                      "control_seconds": fp16_seconds[family]}
            fused_comparisons.append({
                **common, "candidate_seconds": fused_seconds[family],
                **_quality_metrics(fp16_logits[family], fused_logits[family], continuation),
            })
        fused_aggregate = _aggregate(fused_comparisons)
        speed_gain = 100 * (1 - fused_aggregate["total_seconds"] /
                            dynamic_aggregate["total_seconds"])
        acceptance = {
            "fused_top1_within_1pp_of_dynamic":
                fused_aggregate["teacher_forced_top1_agreement_fraction"] >=
                dynamic_aggregate["teacher_forced_top1_agreement_fraction"] - 0.01,
            "fused_top5_within_1pp_of_dynamic":
                fused_aggregate["mean_top5_overlap_fraction"] >=
                dynamic_aggregate["mean_top5_overlap_fraction"] - 0.01,
            "fused_kl_no_more_than_0_002_above_dynamic":
                fused_aggregate["mean_kl_divergence_nats"] <=
                dynamic_aggregate["mean_kl_divergence_nats"] + 0.002,
            "fused_nll_no_more_than_0_02_above_dynamic":
                fused_aggregate["mean_control_token_nll_delta_nats"] <=
                dynamic_aggregate["mean_control_token_nll_delta_nats"] + 0.02,
            "incremental_teacher_time_improved_at_least_15_percent": speed_gain >= 15,
        }
    else:
        fused_aggregate = None
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
              "prompt_manifest_path": str(prompt_manifest) if prompt_manifest else None,
              "prompt_manifest_sha256": _sha256(prompt_manifest) if prompt_manifest else None,
              "families": families,
              "forced_positions": native_aggregate["positions"],
              "native_comparisons": native_comparisons,
              "dynamic_comparisons": dynamic_comparisons,
              "fused_router_gate": args.fused_router_gate,
              "fused_comparisons": fused_comparisons,
              "native_aggregate": native_aggregate,
              "dynamic_aggregate": dynamic_aggregate,
              "fused_aggregate": fused_aggregate,
              ("fused_vs_dynamic_teacher_time_improvement_percent" if args.fused_router_gate
               else "dynamic_vs_native_teacher_time_improvement_percent"): speed_gain,
              "acceptance": acceptance,
              "decision": (("ADVANCE_FUSED_ROUTER_TO_FROZEN_SEMANTIC_GATE"
                            if args.fused_router_gate else
                            "ADVANCE_DYNAMIC_BANK_TO_FROZEN_SEMANTIC_GATE")
                           if all(acceptance.values()) else "STOP_DYNAMIC_BANK_QUALITY"),
              "claim_boundary": (f"Incremental teacher forcing on "
                                 f"{native_aggregate['positions']} positions from "
                                 f"{len(prompts)} frozen families, using opening native-bank "
                                 "histories. This measures probability preservation and speed "
                                 "but not absolute semantic task competence.")}
    report["report_sha256"] = _canonical_sha256(report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output_path), "decision": report["decision"],
                      "native": native_aggregate, "dynamic": dynamic_aggregate,
                      "fused": fused_aggregate,
                      "speed_improvement_percent": speed_gain,
                      "acceptance": acceptance, "report_sha256": report["report_sha256"]},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
