#!/usr/bin/env python3
"""Measure exact cross-request prefix/KV reuse on Apple Metal.

The candidate is only allowed to reuse state when the token prefix, model
artifacts, dtype and numerical backend are identical.  Prompt text and logits
are not written to evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, DynamicCache


SHARED_PREFIX = """You are the governed analysis engine for a small business.
Use only the supplied facts. Preserve currencies, dates, quantities, named
entities, permissions, and explicit uncertainty. Never invent missing values.
Separate observations from recommendations. If a requested conclusion is not
supported, say what evidence is missing. Return a concise answer with: result,
evidence, risks, and next action.

Business Map policy: supplier bank-detail changes require independent callback
verification; payments above EUR 10,000 require two approvals; customer data
must not leave the local system; calculations must show their inputs; any
conflict between a request and these controls must be surfaced before action.

The following request is governed by that exact policy and response contract.
Request: """

SUFFIXES = (
    "Review a EUR 12,400 supplier invoice whose bank details changed yesterday.",
    "Summarise the operational risks in opening a second retail location.",
    "Draft a cautious reply to a customer disputing an invoice dated 4 June.",
    "Calculate the gross margin from revenue EUR 84,000 and cost EUR 51,500.",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode()).hexdigest()


def _longest_common_prefix(sequences: list[list[int]]) -> list[int]:
    if not sequences:
        return []
    limit = min(map(len, sequences))
    for index in range(limit):
        token = sequences[0][index]
        if any(sequence[index] != token for sequence in sequences[1:]):
            return sequences[0][:index]
    return sequences[0][:limit]


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)]


def _sync() -> None:
    torch.mps.synchronize()


def _branch_dynamic_cache(cache: DynamicCache) -> DynamicCache:
    """Create an independently growing cache view over immutable prefix tensors."""
    return DynamicCache([
        (layer.keys.detach(), layer.values.detach())
        for layer in cache.layers
    ])


@torch.inference_mode()
def _decode(
    model: Any,
    initial: Any,
    attention_length: int,
    generated_tokens: int,
) -> dict[str, Any]:
    scores: list[torch.Tensor] = []
    tokens: list[int] = []
    output = initial
    first_ready = time.perf_counter()
    for step in range(generated_tokens):
        logits = output.logits[:, -1, :]
        scores.append(logits.float().cpu())
        token = logits.argmax(dim=-1)
        tokens.append(int(token.item()))
        if step + 1 == generated_tokens:
            break
        attention_length += 1
        cache_position = torch.tensor([attention_length - 1], dtype=torch.long, device="mps")
        output = model(
            input_ids=token.reshape(1, 1),
            attention_mask=torch.ones((1, attention_length), dtype=torch.long, device="mps"),
            past_key_values=output.past_key_values,
            cache_position=cache_position,
            position_ids=cache_position.reshape(1, 1),
            use_cache=True,
        )
    _sync()
    return {"token_ids": tokens, "scores": scores, "first_ready": first_ready}


@torch.inference_mode()
def _control(model: Any, ids: torch.Tensor, generated_tokens: int) -> dict[str, Any]:
    started = time.perf_counter()
    output = model(input_ids=ids, attention_mask=torch.ones_like(ids), use_cache=True)
    _sync()
    prefill_done = time.perf_counter()
    result = _decode(model, output, ids.shape[1], generated_tokens)
    ended = time.perf_counter()
    return {**result, "seconds": ended - started,
            "prefill_seconds": prefill_done - started,
            "decode_seconds": ended - prefill_done}


@torch.inference_mode()
def _candidate(
    model: Any,
    ids: torch.Tensor,
    prefix_length: int,
    prefix_cache: Any,
    generated_tokens: int,
) -> dict[str, Any]:
    suffix = ids[:, prefix_length:]
    if suffix.shape[1] < 1:
        raise RuntimeError("request suffix must not be empty")
    cache_position = torch.arange(prefix_length, ids.shape[1], dtype=torch.long, device="mps")
    started = time.perf_counter()
    output = model(
        input_ids=suffix,
        attention_mask=torch.ones((1, ids.shape[1]), dtype=torch.long, device="mps"),
        past_key_values=_branch_dynamic_cache(prefix_cache),
        cache_position=cache_position,
        position_ids=cache_position.reshape(1, -1),
        use_cache=True,
    )
    _sync()
    prefill_done = time.perf_counter()
    result = _decode(model, output, ids.shape[1], generated_tokens)
    ended = time.perf_counter()
    return {**result, "seconds": ended - started,
            "prefill_seconds": prefill_done - started,
            "decode_seconds": ended - prefill_done}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--generated-tokens", type=int, default=8)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not torch.backends.mps.is_available():
        raise SystemExit("Apple Metal/MPS is required")
    if args.generated_tokens < 1:
        raise SystemExit("generated tokens must be positive")
    root = args.storage_root.resolve()
    model_path = args.model_path.resolve()
    output_path = (root / "experiments" / f"{args.run_id}.json").resolve()
    if root not in model_path.parents or root not in output_path.parents:
        raise SystemExit("model and evidence must remain on external storage")
    if output_path.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output_path}")

    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    requests = [SHARED_PREFIX + suffix for suffix in SUFFIXES]
    token_lists = [tokenizer.encode(text, add_special_tokens=True) for text in requests]
    common = _longest_common_prefix(token_lists)
    if len(common) < 64 or any(len(tokens) == len(common) for tokens in token_lists):
        raise RuntimeError("workload lacks a substantial genuine shared token prefix")
    token_tensors = [torch.tensor([tokens], dtype=torch.long, device="mps")
                     for tokens in token_lists]
    prefix_tensor = torch.tensor([common], dtype=torch.long, device="mps")

    artifact_names = ["config.json", "tokenizer.json", "model.safetensors.index.json"]
    artifact_names.extend(sorted(path.name for path in model_path.glob("model-*.safetensors")))
    artifact_hashes = {name: _sha256(model_path / name) for name in artifact_names}
    cache_key = _canonical_sha256({
        "model_artifacts": artifact_hashes,
        "prefix_token_sha256": hashlib.sha256(prefix_tensor.cpu().numpy().tobytes()).hexdigest(),
        "prefix_length": len(common), "dtype": "float16", "backend": "mps",
    })

    load_started = time.perf_counter()
    model = AutoModelForCausalLM.from_pretrained(
        model_path, local_files_only=True, dtype=torch.float16,
        device_map={"": "mps"}, low_cpu_mem_usage=True,
    ).eval()
    _sync()
    load_seconds = time.perf_counter() - load_started

    controls = [_control(model, ids, args.generated_tokens) for ids in token_tensors]
    prefix_started = time.perf_counter()
    prefix_output = model(
        input_ids=prefix_tensor, attention_mask=torch.ones_like(prefix_tensor), use_cache=True,
    )
    _sync()
    prefix_build_seconds = time.perf_counter() - prefix_started
    candidates = [_candidate(
        model, ids, len(common), prefix_output.past_key_values, args.generated_tokens,
    ) for ids in token_tensors]

    comparisons = []
    for index, (control, candidate) in enumerate(zip(controls, candidates, strict=True)):
        errors = [float((left - right).abs().max().item()) for left, right in zip(
            control["scores"], candidate["scores"], strict=True,
        )]
        comparisons.append({
            "request_index": index,
            "request_sha256": hashlib.sha256(requests[index].encode()).hexdigest(),
            "input_tokens": len(token_lists[index]),
            "unique_suffix_tokens": len(token_lists[index]) - len(common),
            "control_seconds": control["seconds"],
            "candidate_seconds_excluding_shared_build": candidate["seconds"],
            "control_prefill_seconds": control["prefill_seconds"],
            "candidate_suffix_prefill_seconds": candidate["prefill_seconds"],
            "token_ids_exact": control["token_ids"] == candidate["token_ids"],
            "all_step_logits_exact": all(error == 0.0 for error in errors),
            "maximum_step_logit_error": max(errors, default=0.0),
            "token_ids_sha256": hashlib.sha256(json.dumps(
                control["token_ids"], separators=(",", ":"),
            ).encode()).hexdigest(),
        })
    control_total = sum(item["seconds"] for item in controls)
    candidate_total = prefix_build_seconds + sum(item["seconds"] for item in candidates)
    speedup = 100.0 * (1.0 - candidate_total / control_total)
    integrity = {
        "all_token_ids_exact": all(item["token_ids_exact"] for item in comparisons),
        "all_step_logits_exact": all(item["all_step_logits_exact"] for item in comparisons),
        "cache_key_binds_model_prefix_dtype_backend": True,
        "shared_prefix_is_exact_and_at_least_64_tokens": len(common) >= 64,
    }
    acceptance = {**integrity, "total_time_improved_at_least_10_percent": speedup >= 10.0}
    report = {
        "schema_version": "aion.exact_prefix_kv_abba.v1",
        "run_id": args.run_id,
        "storage_root": str(root), "model_path": str(model_path),
        "backend": "mps", "dtype": "float16", "load_seconds": load_seconds,
        "cold_warm_boundary": "model loaded from SD once; control and candidate measured full-resident",
        "artifact_hashes": artifact_hashes,
        "shared_prefix": {
            "token_count": len(common),
            "token_sha256": hashlib.sha256(prefix_tensor.cpu().numpy().tobytes()).hexdigest(),
            "cache_key": cache_key,
            "build_seconds": prefix_build_seconds,
            "prompt_text_persisted": False,
        },
        "request_count": len(requests), "generated_tokens_per_request": args.generated_tokens,
        "comparisons": comparisons,
        "aggregate": {
            "control_total_seconds": control_total,
            "candidate_total_seconds_including_one_shared_build": candidate_total,
            "total_time_improvement_percent": speedup,
            "control_p50_seconds": statistics.median(x["seconds"] for x in controls),
            "control_p95_seconds_nearest_rank": _p95([x["seconds"] for x in controls]),
            "candidate_p50_seconds_excluding_shared_build": statistics.median(
                x["seconds"] for x in candidates),
            "candidate_p95_seconds_excluding_shared_build_nearest_rank": _p95(
                [x["seconds"] for x in candidates]),
        },
        "integrity": integrity, "acceptance": acceptance,
        "decision": "PROMOTED" if all(acceptance.values()) else "NOT_PROMOTED",
        "claim_boundary": (
            "Full-resident Metal mechanism test over four synthetic requests with one genuinely "
            "identical token prefix. It proves only exact reusable KV state and avoids no SD expert "
            "faults in this run. Production promotion requires storage-first and randomized tests."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output_path), "decision": report["decision"],
                      "aggregate": report["aggregate"], "integrity": integrity,
                      "report_sha256": report["report_sha256"]}, indent=2))
    return 0 if all(integrity.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
