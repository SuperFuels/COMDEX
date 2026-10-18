#!/usr/bin/env python3
"""Test repeated full-resident Metal generation before blaming SD execution."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import statistics
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from backend.modules.aion_inference import AdaptiveInferenceRuntime
from backend.scripts.run_aion_storage_first_boot import _memory
from backend.scripts.run_aion_storage_first_multiprompt import (
    PROMPTS,
    _canonical_sha256,
    _generate,
    _step_error_summary,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--prompt-family", required=True)
    parser.add_argument("--generated-tokens", type=int, default=256)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    if not torch.backends.mps.is_available():
        raise SystemExit("Apple Metal/MPS is required")
    if args.generated_tokens < 1 or args.repeats < 2:
        raise SystemExit("generated tokens must be positive and repeats must be at least two")
    root = args.storage_root.resolve()
    model_path = args.model_path.resolve()
    output = (root / "experiments" / f"{args.run_id}.json").resolve()
    if root not in model_path.parents or root not in output.parents:
        raise SystemExit("model and evidence must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    prompt = next(
        (item["prompt"] for item in PROMPTS if item["family"] == args.prompt_family),
        None,
    )
    if prompt is None:
        raise SystemExit(f"unknown prompt family: {args.prompt_family}")

    runtime_root = root / "runtime-evidence" / args.run_id
    routed = AdaptiveInferenceRuntime(
        replay_path=runtime_root / "replay.sqlite3",
        trace_path=runtime_root / "trace.jsonl",
    ).route(prompt)
    if not routed.model_call_required or not routed.fallback_prompt:
        raise RuntimeError("diagnostic prompt did not reach the model")

    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    memory = [_memory("before_full_resident_load")]
    load_started = time.perf_counter()
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        local_files_only=True,
        dtype=torch.float16,
        device_map={"": "mps"},
        low_cpu_mem_usage=True,
    ).eval()
    torch.mps.synchronize()
    load_seconds = time.perf_counter() - load_started
    memory.append(_memory("after_full_resident_load"))

    raw = [
        _generate(model, tokenizer, routed.fallback_prompt, args.generated_tokens)
        for _ in range(args.repeats)
    ]
    baseline = raw[0]
    comparisons = []
    for repeat_index, observed in enumerate(raw[1:], start=2):
        errors = [
            float((actual - expected).abs().max().item())
            for actual, expected in zip(observed["scores"], baseline["scores"], strict=True)
        ]
        different_token_steps = [
            index
            for index, (actual, expected) in enumerate(
                zip(observed["token_ids"], baseline["token_ids"], strict=True)
            )
            if actual != expected
        ]
        comparisons.append({
            "baseline_repeat": 1,
            "observed_repeat": repeat_index,
            "token_ids_exact": not different_token_steps,
            "different_token_step_count": len(different_token_steps),
            "first_different_token_step": (
                different_token_steps[0] if different_token_steps else None
            ),
            "all_step_logits_exact": all(error == 0.0 for error in errors),
            "maximum_step_logit_error": max(errors, default=0.0),
            **_step_error_summary(errors, observed["token_ids"]),
        })

    repeats = []
    for index, result in enumerate(raw, start=1):
        repeats.append({
            "repeat": index,
            "seconds": result["seconds"],
            "tokens_per_second": len(result["token_ids"]) / result["seconds"],
            "time_to_first_token_seconds": result["time_to_first_token_seconds"],
            "token_ids_sha256": hashlib.sha256(
                json.dumps(result["token_ids"], separators=(",", ":")).encode()
            ).hexdigest(),
            "token_ids": result["token_ids"],
        })
        result.pop("scores")

    integrity = {
        "all_repeats_reached_requested_token_count": all(
            len(result["token_ids"]) == args.generated_tokens for result in raw
        ),
        "all_repeated_token_ids_exact": all(item["token_ids_exact"] for item in comparisons),
        "all_repeated_step_logits_exact": all(
            item["all_step_logits_exact"] for item in comparisons
        ),
    }
    throughputs = [item["tokens_per_second"] for item in repeats]
    report = {
        "schema_version": "aion.full_resident_determinism.v1",
        "run_id": args.run_id,
        "storage_root": str(root),
        "model_path": str(model_path),
        "prompt_family": args.prompt_family,
        "model_input_sha256": hashlib.sha256(routed.fallback_prompt.encode()).hexdigest(),
        "generated_tokens_per_repeat": args.generated_tokens,
        "repeat_count": args.repeats,
        "load_seconds": load_seconds,
        "repeats": repeats,
        "comparisons": comparisons,
        "aggregate": {
            "median_tokens_per_second": statistics.median(throughputs),
            "minimum_tokens_per_second": min(throughputs),
            "maximum_tokens_per_second": max(throughputs),
        },
        "memory": memory,
        "integrity": integrity,
        "validation_passed": all(integrity.values()),
        "claim_boundary": (
            "Repeated greedy generation from one full-resident FP16 Granite instance on Metal. "
            "This isolates repeatability of the control path; it does not exercise SD expert loading."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "report_sha256": report["report_sha256"],
        "aggregate": report["aggregate"],
        "integrity": integrity,
        "comparisons": comparisons,
    }, indent=2))
    del model
    gc.collect()
    torch.mps.empty_cache()
    return 0 if report["validation_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
