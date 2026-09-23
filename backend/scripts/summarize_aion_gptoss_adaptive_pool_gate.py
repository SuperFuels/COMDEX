#!/usr/bin/env python3
"""Create a compact, hash-bound comparison of the 120B adaptive-pool gates."""

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


def run_metrics(run: dict, prompt_tokens: int) -> dict:
    tokens = run["tokens"][prompt_tokens:]
    seconds = sum(token["wall_seconds"] for token in tokens)
    intervals = [token["wall_seconds"] for token in tokens]
    return {
        "continuation_positions": len(tokens),
        "continuation_seconds": seconds,
        "continuation_tokens_per_second": len(tokens) / seconds,
        "median_token_seconds": statistics.median(intervals),
        "p95_token_seconds": sorted(intervals)[max(0, int(0.95 * len(intervals)) - 1)],
        "expert_load_seconds": sum(sum(layer["expert_load_seconds"]
                                           for layer in token["layers"]) for token in tokens),
        "attention_seconds": sum(sum(layer["attention_process_seconds"]
                                      for layer in token["layers"]) for token in tokens),
        "moe_seconds": sum(sum(layer["finish_process_seconds"]
                                for layer in token["layers"]) for token in tokens),
        "vocabulary_seconds": sum(token["output_process_seconds"] for token in tokens),
        "store_metric_delta": run["store_metric_delta"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--candidate-before-persistent-output", type=Path, required=True)
    parser.add_argument("--six-thread-four-pass", type=Path)
    parser.add_argument("--parallel-moe", type=Path)
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--prompt-tokens", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite summary")
    control = load_verified(args.control)
    candidate = load_verified(args.candidate)
    before = load_verified(args.candidate_before_persistent_output)
    pool = load_verified(args.pool)
    six_thread = load_verified(args.six_thread_four_pass) if args.six_thread_four_pass else None
    parallel = load_verified(args.parallel_moe) if args.parallel_moe else None
    comparisons = []
    for index, (control_run, candidate_run, before_run) in enumerate(zip(
            (control["run_a"], control["run_b"]),
            (candidate["run_a"], candidate["run_b"]),
            (before["run_a"], before["run_b"]), strict=True)):
        control_metrics = run_metrics(control_run, args.prompt_tokens)
        candidate_metrics = run_metrics(candidate_run, args.prompt_tokens)
        before_metrics = run_metrics(before_run, args.prompt_tokens)
        control_ids = [token["generated_token_id"] for token in control_run["tokens"]]
        candidate_ids = [token["generated_token_id"] for token in candidate_run["tokens"]]
        common = 0
        for left, right in zip(control_ids, candidate_ids, strict=True):
            if left != right:
                break
            common += 1
        comparisons.append({
            "pass": index + 1,
            "control": control_metrics,
            "candidate": candidate_metrics,
            "candidate_before_persistent_output": before_metrics,
            "candidate_vs_control_speedup": (
                control_metrics["continuation_seconds"] /
                candidate_metrics["continuation_seconds"]),
            "persistent_output_candidate_speedup": (
                before_metrics["continuation_seconds"] /
                candidate_metrics["continuation_seconds"]),
            "candidate_tokens_and_logits_unchanged_by_persistent_output": (
                [token["generated_token_id"] for token in before_run["tokens"]] == candidate_ids
                and all(left["logits_sha256"] == right["logits_sha256"]
                        for left, right in zip(before_run["tokens"],
                                               candidate_run["tokens"], strict=True))),
            "candidate_vs_control_common_output_prefix_positions": common,
            "candidate_and_control_complete_token_sequences_equal": control_ids == candidate_ids,
        })
    report = {
        "schema": "aion.gptoss-120b-adaptive-pool-performance-gate.v1",
        "status": "ADVANCE_BROADER_QUALITY_GATE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "prompt_tokens": args.prompt_tokens,
        "total_positions": len(candidate["run_a"]["tokens"]),
        "sources": {name: {"path": str(path.resolve()),
                            "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "canonical_sha256": value["canonical_sha256"]}
                    for name, path, value in (
                        ("unrestricted_control", args.control, control),
                        ("adaptive_candidate", args.candidate, candidate),
                        ("candidate_before_persistent_output",
                         args.candidate_before_persistent_output, before),
                        ("adaptive_pool", args.pool, pool))},
        "pool": {key: pool[key] for key in (
            "capacity_bytes", "resident_raw_bytes", "required_prefix_experts",
            "total_layer_experts", "minimum_experts_per_layer",
            "maximum_experts_per_layer")},
        "one_time_pool_preload_seconds": candidate["constrained_expert_pool_preload_seconds"],
        "comparisons": comparisons,
        "acceptance": {
            "mechanism_repeatable": candidate["routes_repeatable"] is True,
            "candidate_internal_logits_bitwise_repeatable": candidate[
                "final_hidden_and_logits_bitwise_repeatable"] is True,
            "zero_candidate_execution_faults": all(
                item["candidate"]["store_metric_delta"]["faults"] == 0
                for item in comparisons),
            "zero_candidate_execution_sd_bytes": all(
                item["candidate"]["store_metric_delta"]["compressed_bytes_read"] == 0
                for item in comparisons),
            "persistent_output_exact_within_candidate": all(
                item["candidate_tokens_and_logits_unchanged_by_persistent_output"]
                for item in comparisons),
            "broad_semantic_quality_passed": False,
        },
        "decision_rule": (
            "Advance performance engineering but do not promote the constrained model until "
            "multiple frozen, representative prompts establish semantic quality. Wording "
            "divergence from unrestricted GPT-OSS is permitted only in this explicitly labelled "
            "quality track."
        ),
        "claim_boundary": (
            "This is genuine later-token execution of a 36-layer GPT-OSS 120B-derived subnetwork "
            "using only original weights and a constrained resident expert pool. It is not "
            "bit-exact unrestricted GPT-OSS 120B and not yet a quality promotion."
        ),
    }
    if six_thread:
        six_runs = [six_thread["run_a"], six_thread["run_b"],
                    *six_thread.get("additional_runs", [])]
        six_metrics = [run_metrics(run, args.prompt_tokens) for run in six_runs]
        report["six_thread_replication"] = {
            "source": {
                "path": str(args.six_thread_four_pass.resolve()),
                "file_sha256": hashlib.sha256(args.six_thread_four_pass.read_bytes()).hexdigest(),
                "canonical_sha256": six_thread["canonical_sha256"],
            },
            "passes": six_metrics,
            "post_warmup_tokens_per_second": [
                item["continuation_tokens_per_second"] for item in six_metrics[1:]
            ],
            "post_warmup_median_tokens_per_second": statistics.median(
                item["continuation_tokens_per_second"] for item in six_metrics[1:]),
            "all_routes_hidden_logits_and_tokens_repeatable": (
                six_thread["routes_repeatable"] is True
                and six_thread["final_hidden_and_logits_bitwise_repeatable"] is True),
        }
    if parallel:
        parallel_metrics = [run_metrics(parallel[name], args.prompt_tokens)
                            for name in ("run_a", "run_b")]
        report["parallel_moe_falsification"] = {
            "source": {
                "path": str(args.parallel_moe.resolve()),
                "file_sha256": hashlib.sha256(args.parallel_moe.read_bytes()).hexdigest(),
                "canonical_sha256": parallel["canonical_sha256"],
            },
            "passes": parallel_metrics,
            "bitwise_exact_to_serial_candidate": all(
                all(left["generated_token_id"] == right["generated_token_id"]
                    and left["logits_sha256"] == right["logits_sha256"]
                    and left["final_hidden_sha256"] == right["final_hidden_sha256"]
                    for left, right in zip(candidate[name]["tokens"], parallel[name]["tokens"],
                                           strict=True))
                for name in ("run_a", "run_b")),
            "decision": "STOP_SUSTAINED_PARALLEL_EXPERTS",
            "reason": "Memory-bandwidth and CPU contention made both sustained passes slower.",
        }
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "comparisons": [{
        "candidate_tps": item["candidate"]["continuation_tokens_per_second"],
        "speedup": item["candidate_vs_control_speedup"]} for item in comparisons],
        "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
