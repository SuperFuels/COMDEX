#!/usr/bin/env python3
"""Post-hoc choice-likelihood diagnostic for FP16 and INT8 Glyph Granite.

This deliberately reuses the previously observed MCQ cohort.  It can diagnose
free-generation/formatting failure, but it cannot promote the INT8 candidate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from backend.modules.aion_inference.int8_glyph_moe import Int8GlyphMoE, load_layer_entries
from backend.scripts.run_aion_int8_glyph_full_model import _canonical_sha256
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256
from backend.scripts.run_aion_storage_first_multiprompt import _chat_tokens


CHOICES = ("A", "B", "C", "D")


def _choice_token_ids(tokenizer: Any) -> dict[str, tuple[int, ...]]:
    """Return bare and space-prefixed single-token spellings per choice."""
    result: dict[str, tuple[int, ...]] = {}
    for choice in CHOICES:
        ids = []
        for spelling in (choice, f" {choice}"):
            encoded = tokenizer.encode(spelling, add_special_tokens=False)
            if len(encoded) != 1:
                raise ValueError(f"choice spelling {spelling!r} is not one token: {encoded}")
            ids.append(encoded[0])
        result[choice] = tuple(dict.fromkeys(ids))
    return result


def _select_choice(last_logits: torch.Tensor,
                   token_ids: dict[str, tuple[int, ...]]) -> tuple[str, dict[str, float], float]:
    """Choose by combined probability mass of valid one-token spellings."""
    scores = {
        choice: float(torch.logsumexp(last_logits[list(ids)].float(), dim=0).item())
        for choice, ids in token_ids.items()
    }
    ordered = sorted(scores, key=scores.get, reverse=True)
    return ordered[0], scores, scores[ordered[0]] - scores[ordered[1]]


@torch.inference_mode()
def _run(model: Any, tokenizer: Any, cases: list[dict[str, str]],
         token_ids: dict[str, tuple[int, ...]]) -> list[dict[str, Any]]:
    results = []
    for case in cases:
        prompt = case["question"] + "\nRespond with only the single capital letter A, B, C, or D."
        inputs = _chat_tokens(tokenizer, prompt)
        started = time.perf_counter()
        logits = model(**inputs, use_cache=False).logits[0, -1]
        torch.mps.synchronize()
        seconds = time.perf_counter() - started
        observed, scores, margin = _select_choice(logits, token_ids)
        results.append({"id": case["id"], "family": case["family"],
                        "expected": case["answer"], "observed": observed,
                        "passed": observed == case["answer"], "seconds": seconds,
                        "choice_logit_scores": scores, "winning_margin": margin})
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--glyph-manifest", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"model": args.model_path.resolve(), "source_manifest": args.source_manifest.resolve(),
             "glyph_manifest": args.glyph_manifest.resolve(), "tasks": args.tasks.resolve()}
    output = args.output.resolve()
    if any(root not in paths[name].parents for name in ("model", "source_manifest", "glyph_manifest")):
        raise SystemExit("model artifacts must remain on external storage")
    if output.exists() or root not in output.parents:
        raise SystemExit("evidence must be new and on external storage")

    cases = json.loads(paths["tasks"].read_text())["cases"]
    glyph = json.loads(paths["glyph_manifest"].read_text())
    tokenizer = AutoTokenizer.from_pretrained(paths["model"], local_files_only=True)
    token_ids = _choice_token_ids(tokenizer)
    model = AutoModelForCausalLM.from_pretrained(
        paths["model"], local_files_only=True, dtype=torch.float16,
        device_map={"": "mps"}, low_cpu_mem_usage=True,
    ).eval()
    controls = _run(model, tokenizer, cases, token_ids)
    for layer_index, layer in enumerate(model.model.layers):
        entries = load_layer_entries(glyph, layer_index, root, _sha256)
        layer.block_sparse_moe = Int8GlyphMoE(layer.block_sparse_moe, entries, root, _sha256, "mps")
    torch.mps.synchronize()
    candidates = _run(model, tokenizer, cases, token_ids)

    control_passes = sum(item["passed"] for item in controls)
    candidate_passes = sum(item["passed"] for item in candidates)
    answer_matches = sum(left["observed"] == right["observed"]
                         for left, right in zip(controls, candidates, strict=True))
    comparisons = [{"id": left["id"], "family": left["family"],
                    "expected": left["expected"], "control_observed": left["observed"],
                    "candidate_observed": right["observed"], "control_passed": left["passed"],
                    "candidate_passed": right["passed"],
                    "control_winning_margin": left["winning_margin"],
                    "candidate_winning_margin": right["winning_margin"]}
                   for left, right in zip(controls, candidates, strict=True)]
    diagnostic_checks = {
        "fp16_passed_at_least_10_of_12": control_passes >= 10,
        "int8_lost_at_most_one_fp16_pass": candidate_passes >= control_passes - 1,
        "answer_agreement_at_least_90_percent": answer_matches / len(cases) >= 0.9,
    }
    report = {
        "schema_version": "aion.int8_choice_likelihood_diagnostic.v1",
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": {name: _sha256(path) for name, path in paths.items() if path.is_file()},
        "choice_token_ids": {key: list(value) for key, value in token_ids.items()},
        "control": {"passes": control_passes, "total_seconds": sum(x["seconds"] for x in controls)},
        "candidate": {"passes": candidate_passes,
                      "total_seconds": sum(x["seconds"] for x in candidates)},
        "answer_agreement_fraction": answer_matches / len(cases),
        "comparisons": comparisons,
        "diagnostic_checks": diagnostic_checks,
        "decision": ("SUPPORTS_FREEZING_UNSEEN_HOLDOUT"
                     if all(diagnostic_checks.values()) else "DIAGNOSTIC_DID_NOT_CLEAR_BASELINE"),
        "claim_boundary": (
            "Post-hoc diagnostic on the already-observed twelve-case cohort. It tests whether "
            "free-generation formatting obscured choice competence; it cannot promote INT8 or "
            "establish general semantic quality. A newly frozen unseen cohort is mandatory."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "decision": report["decision"],
                      "control": report["control"], "candidate": report["candidate"],
                      "answer_agreement_fraction": report["answer_agreement_fraction"],
                      "diagnostic_checks": diagnostic_checks,
                      "report_sha256": report["report_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
