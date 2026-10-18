#!/usr/bin/env python3
"""Bind exact-prefill/constrained-continuation speed and quality evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path


def canonical(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()


def load_verified(path: Path) -> dict:
    value = json.loads(path.read_text())
    claimed = value.get("canonical_sha256")
    body = dict(value)
    body.pop("canonical_sha256", None)
    if claimed != canonical(body):
        raise ValueError(f"canonical hash mismatch: {path}")
    return value


def metrics(run: dict, prompt_positions: int) -> dict:
    tokens = run["tokens"][prompt_positions:]
    seconds = sum(token["wall_seconds"] for token in tokens)
    latencies = [token["wall_seconds"] for token in tokens]
    return {
        "positions": len(tokens),
        "seconds": seconds,
        "tokens_per_second": len(tokens) / seconds,
        "median_token_seconds": statistics.median(latencies),
        "p95_token_seconds": sorted(latencies)[max(0, int(0.95 * len(latencies)) - 1)],
        "expert_load_seconds": sum(
            sum(layer["expert_load_seconds"] for layer in token["layers"])
            for token in tokens),
        "moe_seconds": sum(
            sum(layer["finish_process_seconds"] for layer in token["layers"])
            for token in tokens),
        "attention_seconds": sum(
            sum(layer["attention_process_seconds"] for layer in token["layers"])
            for token in tokens),
        "vocabulary_seconds": sum(token["output_process_seconds"] for token in tokens),
    }


def source(path: Path, value: dict) -> dict:
    return {
        "path": str(path.resolve()),
        "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "canonical_sha256": value["canonical_sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--prompt-positions", type=int, required=True)
    parser.add_argument("--expected-text", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite summary")
    control = load_verified(args.control)
    candidate = load_verified(args.candidate)
    receipt = load_verified(args.receipt)
    pool = load_verified(args.pool)
    comparisons = []
    prompt_exact = True
    for name in ("run_a", "run_b"):
        control_run = control[name]
        candidate_run = candidate[name]
        prompt_equal = all(
            left["generated_token_id"] == right["generated_token_id"]
            and left["final_hidden_sha256"] == right["final_hidden_sha256"]
            and left["logits_sha256"] == right["logits_sha256"]
            for left, right in zip(control_run["tokens"][:args.prompt_positions],
                                   candidate_run["tokens"][:args.prompt_positions], strict=True))
        prompt_exact &= prompt_equal
        control_metrics = metrics(control_run, args.prompt_positions)
        candidate_metrics = metrics(candidate_run, args.prompt_positions)
        comparisons.append({
            "pass": name,
            "prompt_bit_exact_to_unrestricted": prompt_equal,
            "control": control_metrics,
            "candidate": candidate_metrics,
            "candidate_speedup": (control_metrics["tokens_per_second"]
                                  / candidate_metrics["tokens_per_second"]) ** -1,
            "candidate_rehydrate_seconds": candidate_run[
                "prompt_to_continuation_rehydrate_seconds"],
            "candidate_rehydrate_metric_delta": candidate_run[
                "prompt_to_continuation_rehydrate_metric_delta"],
        })
    expected_present = args.expected_text in receipt["generated_text"]
    acceptance = {
        "prompt_bit_exact_to_unrestricted_both_passes": prompt_exact,
        "candidate_routes_hidden_logits_and_tokens_repeatable": (
            candidate["routes_repeatable"] is True
            and candidate["final_hidden_and_logits_bitwise_repeatable"] is True),
        "expected_arithmetic_answer_present": expected_present,
        "receipt_passed": receipt["status"] == "PASSED",
        "continuation_expert_load_under_50ms_both_passes": all(
            item["candidate"]["expert_load_seconds"] < 0.05 for item in comparisons),
        "candidate_above_2_tokens_per_second_both_passes": all(
            item["candidate"]["tokens_per_second"] > 2.0 for item in comparisons),
    }
    report = {
        "schema": "aion.gptoss-120b-exact-prefill-quality-gate.v1",
        "status": "PASSED_NARROW_ARITHMETIC" if all(acceptance.values()) else "FAILED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "architecture": "unrestricted exact prompt prefill, rehydrated constrained continuation",
        "prompt_positions": args.prompt_positions,
        "expected_text": args.expected_text,
        "generated_text": receipt["generated_text"],
        "sources": {
            "unrestricted_control": source(args.control, control),
            "candidate": source(args.candidate, candidate),
            "detokenized_receipt": source(args.receipt, receipt),
            "expert_pool": source(args.pool, pool),
        },
        "initial_pool_preload_seconds": candidate["constrained_expert_pool_preload_seconds"],
        "pool_raw_bytes": pool["resident_raw_bytes"],
        "comparisons": comparisons,
        "acceptance": acceptance,
        "decision": "ADVANCE_MULTI_FAMILY_QUALITY_AND_OVERLAPPED_REHYDRATION",
        "claim_boundary": (
            "The prompt state is bit-exact to unrestricted GPT-OSS 120B and the arithmetic "
            "answer is correct. Autoregressive routing is constrained to a request-derived "
            "pool of original experts, so continuation is not exact unrestricted 120B. This "
            "single arithmetic prompt is a narrow quality pass, not general model validation."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": report["status"],
        "candidate_tps": [item["candidate"]["tokens_per_second"] for item in comparisons],
        "speedups": [item["candidate_speedup"] for item in comparisons],
        "canonical_sha256": report["canonical_sha256"],
    }, sort_keys=True))
    return 0 if all(acceptance.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
