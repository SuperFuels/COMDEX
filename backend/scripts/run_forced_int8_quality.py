#!/usr/bin/env python3
"""Compare FP16 and INT8 Granite on identical teacher-forced histories."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from backend.modules.aion_inference.int8_glyph_moe import Int8GlyphMoE, load_layer_entries
from backend.scripts.run_aion_int8_glyph_full_model import _canonical_sha256
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256
from backend.scripts.run_aion_storage_first_boot import _verify_source_checkpoint
from backend.scripts.run_aion_storage_first_multiprompt import PROMPTS, _chat_tokens


@torch.inference_mode()
def _teacher_logits(model: Any, prompt_ids: torch.Tensor,
                    continuation: list[int]) -> tuple[torch.Tensor, float]:
    continuation_tensor = torch.tensor([continuation], dtype=torch.long, device="mps")
    full_ids = torch.cat((prompt_ids, continuation_tensor), dim=1)
    started = time.perf_counter()
    output = model(input_ids=full_ids, attention_mask=torch.ones_like(full_ids), use_cache=False)
    torch.mps.synchronize()
    seconds = time.perf_counter() - started
    start = prompt_ids.shape[1] - 1
    stop = start + len(continuation)
    return output.logits[0, start:stop].detach().float().cpu(), seconds


def _quality_metrics(control: torch.Tensor, candidate: torch.Tensor,
                     continuation: list[int]) -> dict[str, Any]:
    control_logp = torch.log_softmax(control, dim=-1)
    candidate_logp = torch.log_softmax(candidate, dim=-1)
    control_p = control_logp.exp()
    kl = (control_p * (control_logp - candidate_logp)).sum(dim=-1)
    control_top1 = control.argmax(dim=-1)
    candidate_top1 = candidate.argmax(dim=-1)
    agreement = control_top1 == candidate_top1
    control_top5 = control.topk(5, dim=-1).indices
    candidate_top5 = candidate.topk(5, dim=-1).indices
    overlaps = []
    for left, right in zip(control_top5, candidate_top5, strict=True):
        overlaps.append(len(set(left.tolist()) & set(right.tolist())) / 5)
    targets = torch.tensor(continuation, dtype=torch.long)
    indexes = torch.arange(len(continuation))
    control_nll = -control_logp[indexes, targets]
    candidate_nll = -candidate_logp[indexes, targets]
    margins = control.topk(2, dim=-1).values
    margin = margins[:, 0] - margins[:, 1]
    disagreement_margins = margin[~agreement]
    return {
        "positions": len(continuation),
        "top1_agreement_count": int(agreement.sum()),
        "top1_agreement_fraction": float(agreement.float().mean()),
        "mean_top5_overlap_fraction": statistics.mean(overlaps),
        "mean_kl_divergence_nats": float(kl.mean()),
        "p95_kl_divergence_nats": float(torch.quantile(kl, 0.95)),
        "mean_control_token_nll_delta_nats": float((candidate_nll - control_nll).mean()),
        "maximum_absolute_logit_error": float((candidate - control).abs().max()),
        "mean_fp16_margin_at_disagreement": (
            float(disagreement_margins.mean()) if disagreement_margins.numel() else None
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--glyph-manifest", type=Path, required=True)
    parser.add_argument("--generation-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"model": args.model_path.resolve(),
             "source_manifest": args.source_manifest.resolve(),
             "glyph_manifest": args.glyph_manifest.resolve(),
             "generation_evidence": args.generation_evidence.resolve()}
    output = args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all model inputs and evidence must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    source = json.loads(paths["source_manifest"].read_text())
    glyph = json.loads(paths["glyph_manifest"].read_text())
    generation = json.loads(paths["generation_evidence"].read_text())
    if not all(source["integrity"].values()) or not all(glyph["integrity"].values()):
        raise RuntimeError("manifest integrity failed")
    if glyph["source_manifest_sha256"] != _sha256(paths["source_manifest"]):
        raise RuntimeError("Glyph/source binding failed")
    verification = _verify_source_checkpoint(root, source)
    if not verification["passed"]:
        raise RuntimeError("checkpoint verification failed")
    by_family = {item["family"]: item for item in generation["comparisons"]}
    generated_tokens = int(generation["generated_tokens_per_prompt"])

    tokenizer = AutoTokenizer.from_pretrained(paths["model"], local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        paths["model"], local_files_only=True, dtype=torch.float16,
        device_map={"": "mps"}, low_cpu_mem_usage=True,
    ).eval()
    control_logits = {}
    control_seconds = {}
    prompt_ids = {}
    for prompt in PROMPTS:
        family = prompt["family"]
        ids = _chat_tokens(tokenizer, prompt["prompt"])["input_ids"]
        prompt_ids[family] = ids
        logits, seconds = _teacher_logits(
            model, ids, by_family[family]["control_token_ids"],
        )
        control_logits[family] = logits
        control_seconds[family] = seconds

    install_started = time.perf_counter()
    for layer_index, layer in enumerate(model.model.layers):
        entries = load_layer_entries(glyph, layer_index, root, _sha256)
        layer.block_sparse_moe = Int8GlyphMoE(
            layer.block_sparse_moe, entries, root, _sha256, "mps",
        )
    torch.mps.synchronize()
    install_seconds = time.perf_counter() - install_started
    comparisons = []
    for prompt in PROMPTS:
        family = prompt["family"]
        continuation = by_family[family]["control_token_ids"]
        candidate_logits, candidate_seconds = _teacher_logits(
            model, prompt_ids[family], continuation,
        )
        comparisons.append({
            "family": family,
            "prompt_sha256": hashlib.sha256(prompt["prompt"].encode()).hexdigest(),
            "control_seconds": control_seconds[family],
            "candidate_seconds": candidate_seconds,
            **_quality_metrics(control_logits[family], candidate_logits, continuation),
        })
    total_positions = sum(item["positions"] for item in comparisons)
    top1 = sum(item["top1_agreement_count"] for item in comparisons) / total_positions
    mean_kl = sum(item["mean_kl_divergence_nats"] * item["positions"]
                  for item in comparisons) / total_positions
    nll_delta = sum(item["mean_control_token_nll_delta_nats"] * item["positions"]
                    for item in comparisons) / total_positions
    top5 = sum(item["mean_top5_overlap_fraction"] * item["positions"]
               for item in comparisons) / total_positions
    acceptance = {
        "teacher_forced_top1_agreement_at_least_90_percent": top1 >= 0.90,
        "mean_top5_overlap_at_least_90_percent": top5 >= 0.90,
        "mean_kl_divergence_at_most_0_02_nats": mean_kl <= 0.02,
        "control_token_nll_delta_at_most_0_10_nats": nll_delta <= 0.10,
    }
    report = {
        "schema_version": "aion.teacher_forced_int8_quality.v1",
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": {name: _sha256(path) for name, path in paths.items() if path.is_file()},
        "source_verification": verification,
        "generated_tokens_per_family": generated_tokens,
        "families": [item["family"] for item in PROMPTS],
        "glyph_install_seconds": install_seconds,
        "comparisons": comparisons,
        "aggregate": {"teacher_forced_top1_agreement_fraction": top1,
                      "mean_top5_overlap_fraction": top5,
                      "mean_kl_divergence_nats": mean_kl,
                      "mean_control_token_nll_delta_nats": nll_delta},
        "acceptance": acceptance,
        "decision": "ADVANCE_TO_SEMANTIC_TASK_GATE" if all(acceptance.values())
                    else "NOT_PROMOTED",
        "claim_boundary": (
            "Teacher-forced comparison on FP16-generated histories from four frozen prompts. "
            "It diagnoses probability preservation but does not establish semantic task quality."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "decision": report["decision"],
                      "aggregate": report["aggregate"], "acceptance": acceptance,
                      "report_sha256": report["report_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
