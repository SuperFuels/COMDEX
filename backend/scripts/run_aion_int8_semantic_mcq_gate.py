#!/usr/bin/env python3
"""Frozen multiple-choice quality gate for FP16 and INT8 Glyph Granite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import time
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from backend.modules.aion_inference.int8_glyph_moe import Int8GlyphMoE, load_layer_entries
from backend.scripts.run_aion_int8_glyph_full_model import _canonical_sha256
from backend.scripts.run_aion_moe_end_to_end_fault_in import _sha256
from backend.scripts.run_aion_storage_first_multiprompt import _chat_tokens


def _choice(text: str) -> str | None:
    match = re.search(r"\b([ABCD])\b", text.upper())
    return match.group(1) if match else None


@torch.inference_mode()
def _run(model: Any, tokenizer: Any, cases: list[dict[str, str]]) -> list[dict[str, Any]]:
    results = []
    for case in cases:
        prompt = case["question"] + "\nRespond with only the single capital letter A, B, C, or D."
        inputs = _chat_tokens(tokenizer, prompt)
        started = time.perf_counter()
        generated = model.generate(**inputs, do_sample=False, max_new_tokens=8, use_cache=True,
                                   pad_token_id=tokenizer.eos_token_id)
        torch.mps.synchronize()
        seconds = time.perf_counter() - started
        continuation = generated[0, inputs["input_ids"].shape[1]:].detach().cpu()
        observed = _choice(tokenizer.decode(continuation))
        results.append({"id": case["id"], "family": case["family"],
                        "expected": case["answer"], "observed": observed,
                        "passed": observed == case["answer"],
                        "token_count": len(continuation), "seconds": seconds})
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
    model = AutoModelForCausalLM.from_pretrained(
        paths["model"], local_files_only=True, dtype=torch.float16,
        device_map={"": "mps"}, low_cpu_mem_usage=True,
    ).eval()
    controls = _run(model, tokenizer, cases)
    for layer_index, layer in enumerate(model.model.layers):
        entries = load_layer_entries(glyph, layer_index, root, _sha256)
        layer.block_sparse_moe = Int8GlyphMoE(layer.block_sparse_moe, entries, root, _sha256, "mps")
    torch.mps.synchronize()
    candidates = _run(model, tokenizer, cases)
    control_passes = sum(item["passed"] for item in controls)
    candidate_passes = sum(item["passed"] for item in candidates)
    answer_matches = sum(left["observed"] == right["observed"]
                         for left, right in zip(controls, candidates, strict=True))
    control_tps = sum(x["token_count"] for x in controls) / sum(x["seconds"] for x in controls)
    candidate_tps = sum(x["token_count"] for x in candidates) / sum(x["seconds"] for x in candidates)
    comparisons = [{"id": left["id"], "family": left["family"],
                    "expected": left["expected"], "control_observed": left["observed"],
                    "candidate_observed": right["observed"], "control_passed": left["passed"],
                    "candidate_passed": right["passed"]}
                   for left, right in zip(controls, candidates, strict=True)]
    acceptance = {"fp16_passed_at_least_10_of_12": control_passes >= 10,
                  "int8_passed_at_least_10_of_12": candidate_passes >= 10,
                  "int8_lost_at_most_one_fp16_pass": candidate_passes >= control_passes - 1,
                  "answer_agreement_at_least_90_percent": answer_matches / len(cases) >= 0.9,
                  "throughput_not_regressed_more_than_5_percent": candidate_tps >= control_tps * 0.95}
    report = {"schema_version": "aion.int8_semantic_mcq_gate.v1",
              "paths": {name: str(path) for name, path in paths.items()},
              "hashes": {name: _sha256(path) for name, path in paths.items() if path.is_file()},
              "control": {"passes": control_passes, "tokens_per_second": control_tps},
              "candidate": {"passes": candidate_passes, "tokens_per_second": candidate_tps},
              "answer_agreement_fraction": answer_matches / len(cases),
              "comparisons": comparisons, "acceptance": acceptance,
              "decision": "ADVANCE_TO_RANDOMIZED_LONG_GATE" if all(acceptance.values()) else "NOT_PROMOTED",
              "claim_boundary": "Twelve frozen synthetic multiple-choice microtasks; not broad generative quality or exact equivalence."}
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "decision": report["decision"],
                      "control": report["control"], "candidate": report["candidate"],
                      "answer_agreement_fraction": report["answer_agreement_fraction"],
                      "acceptance": acceptance, "report_sha256": report["report_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
