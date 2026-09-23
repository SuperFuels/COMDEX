#!/usr/bin/env python3
"""Frozen general semantic task gate for the quality-gated INT8 Glyph model."""

from __future__ import annotations

import argparse
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
from backend.scripts.run_aion_storage_first_multiprompt import _chat_tokens


def _extract_json(text: str) -> Any | None:
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
            return value
        except json.JSONDecodeError:
            pass
    return None


def _equivalent(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and set(actual) == set(expected) and all(
            _equivalent(actual[key], value) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            _equivalent(left, right) for left, right in zip(actual, expected, strict=True)
        )
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return isinstance(actual, (int, float)) and abs(float(actual) - float(expected)) <= 0.01
    return actual == expected


@torch.inference_mode()
def _run(model: Any, tokenizer: Any, cases: list[dict[str, Any]], tokens: int) -> list[dict[str, Any]]:
    results = []
    for case in cases:
        inputs = _chat_tokens(tokenizer, case["prompt"])
        started = time.perf_counter()
        generated = model.generate(**inputs, do_sample=False, max_new_tokens=tokens,
                                   use_cache=True, pad_token_id=tokenizer.eos_token_id)
        torch.mps.synchronize()
        seconds = time.perf_counter() - started
        continuation = generated[0, inputs["input_ids"].shape[1]:].detach().cpu()
        parsed = _extract_json(tokenizer.decode(continuation))
        results.append({"id": case["id"], "family": case["family"],
                        "passed": _equivalent(parsed, case["expected"]),
                        "parsed": parsed, "generated_tokens": len(continuation),
                        "seconds": seconds})
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--glyph-manifest", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--generated-tokens", type=int, default=64)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"model": args.model_path.resolve(), "source_manifest": args.source_manifest.resolve(),
             "glyph_manifest": args.glyph_manifest.resolve(), "tasks": args.tasks.resolve()}
    output = args.output.resolve()
    if root not in paths["model"].parents or root not in paths["source_manifest"].parents or root not in paths["glyph_manifest"].parents:
        raise SystemExit("model artifacts must remain on external storage")
    if output.exists() or root not in output.parents:
        raise SystemExit("evidence must be new and on external storage")
    tasks = json.loads(paths["tasks"].read_text())
    cases = tasks["cases"]
    tokenizer = AutoTokenizer.from_pretrained(paths["model"], local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        paths["model"], local_files_only=True, dtype=torch.float16,
        device_map={"": "mps"}, low_cpu_mem_usage=True,
    ).eval()
    controls = _run(model, tokenizer, cases, args.generated_tokens)
    for layer_index, layer in enumerate(model.model.layers):
        entries = load_layer_entries(
            json.loads(paths["glyph_manifest"].read_text()), layer_index, root, _sha256,
        )
        layer.block_sparse_moe = Int8GlyphMoE(layer.block_sparse_moe, entries, root, _sha256, "mps")
    torch.mps.synchronize()
    candidates = _run(model, tokenizer, cases, args.generated_tokens)
    control_passes = sum(item["passed"] for item in controls)
    candidate_passes = sum(item["passed"] for item in candidates)
    control_tps = sum(x["generated_tokens"] for x in controls) / sum(x["seconds"] for x in controls)
    candidate_tps = sum(x["generated_tokens"] for x in candidates) / sum(x["seconds"] for x in candidates)
    comparisons = []
    for control, candidate in zip(controls, candidates, strict=True):
        comparisons.append({"id": control["id"], "family": control["family"],
                            "control_passed": control["passed"],
                            "candidate_passed": candidate["passed"],
                            "outputs_equal": control["parsed"] == candidate["parsed"],
                            "control_seconds": control["seconds"],
                            "candidate_seconds": candidate["seconds"]})
    acceptance = {"fp16_passed_at_least_7_of_8": control_passes >= 7,
                  "int8_passed_at_least_7_of_8": candidate_passes >= 7,
                  "int8_did_not_lose_passed_tasks": candidate_passes >= control_passes,
                  "int8_throughput_not_regressed": candidate_tps >= control_tps * 0.95}
    report = {"schema_version": "aion.int8_semantic_gate.v1",
              "paths": {name: str(path) for name, path in paths.items()},
              "hashes": {name: _sha256(path) for name, path in paths.items() if path.is_file()},
              "case_count": len(cases), "generated_token_limit": args.generated_tokens,
              "control": {"passes": control_passes, "tokens_per_second": control_tps},
              "candidate": {"passes": candidate_passes, "tokens_per_second": candidate_tps},
              "comparisons": comparisons, "acceptance": acceptance,
              "decision": "ADVANCE_TO_RANDOMIZED_LONG_GATE" if all(acceptance.values()) else "NOT_PROMOTED",
              "claim_boundary": "Eight frozen synthetic JSON microtasks; not broad language quality, natural prompts, or exact equivalence."}
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "decision": report["decision"],
                      "control": report["control"], "candidate": report["candidate"],
                      "acceptance": acceptance, "report_sha256": report["report_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
