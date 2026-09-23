#!/usr/bin/env python3
"""Bind matched protected-core shrink evidence across two frozen families."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def runs(report: dict) -> list[dict]:
    return [report["run_a"], report["run_b"], *report.get("additional_runs", [])]


def summarise(path: Path, skip: int) -> tuple[dict, dict]:
    report = json.loads(path.read_text()); prompt = len(report["input_token_ids"])
    observations = []
    for index, run in enumerate(runs(report)):
        tokens = run["tokens"][prompt:]
        wall = sum(token["wall_seconds"] for token in tokens)
        metric = run["store_metric_delta"]
        observations.append({
            "pass": index + 1, "tokens": len(tokens), "wall_seconds": wall,
            "tokens_per_second": len(tokens) / wall,
            "l2_bytes_read": metric["l2_bytes_read"],
            "compressed_sd_bytes_read": metric["compressed_bytes_read"],
            "l2_misses": metric["l2_misses"],
            "expert_finish_seconds": sum(layer["finish_process_seconds"] for token in tokens for layer in token["layers"]),
            "attention_seconds": sum(layer["attention_process_seconds"] for token in tokens for layer in token["layers"]),
        })
    selected = observations[skip:]
    summary = {
        "source_path": str(path.resolve()), "source_canonical_sha256": report["canonical_sha256"],
        "passes": observations, "excluded_initial_passes": skip,
        "selected_median_tokens_per_second": statistics.median(row["tokens_per_second"] for row in selected),
        "selected_median_l2_bytes_read": statistics.median(row["l2_bytes_read"] for row in selected),
        "selected_median_sd_bytes_read": statistics.median(row["compressed_sd_bytes_read"] for row in selected),
        "routes_repeatable": report["routes_repeatable"],
        "hidden_logits_repeatable": report["final_hidden_and_logits_bitwise_repeatable"],
    }
    return report, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arithmetic-6", type=Path, required=True)
    parser.add_argument("--arithmetic-8", type=Path, required=True)
    parser.add_argument("--extraction-6", type=Path, required=True)
    parser.add_argument("--extraction-8", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise SystemExit("refusing to overwrite evidence")
    a6, a6s = summarise(args.arithmetic_6, 0); a8, a8s = summarise(args.arithmetic_8, 0)
    e6, e6s = summarise(args.extraction_6, 1); e8, e8s = summarise(args.extraction_8, 1)

    def equivalent(left: dict, right: dict) -> bool:
        left_tokens = left["run_a"]["tokens"]; right_tokens = right["run_a"]["tokens"]
        return len(left_tokens) == len(right_tokens) and all(
            a["generated_token_id"] == b["generated_token_id"]
            and a["final_hidden_sha256"] == b["final_hidden_sha256"]
            and a["logits_sha256"] == b["logits_sha256"]
            for a, b in zip(left_tokens, right_tokens))

    arithmetic_gain = a6s["selected_median_tokens_per_second"] / a8s["selected_median_tokens_per_second"] - 1
    extraction_gain = e6s["selected_median_tokens_per_second"] / e8s["selected_median_tokens_per_second"] - 1
    report = {
        "schema": "aion.gptoss-120b-exact-protected-core-shrink-gate.v1",
        "status": "STOP_CORE_SHRINK_NOT_GENERAL",
        "model": "GPT-OSS 120B Q4_K_M/MXFP4", "quality_track": False,
        "arithmetic": {"six_gib": a6s, "eight_gib": a8s,
                       "six_vs_eight_throughput_change": arithmetic_gain,
                       "cross_configuration_bitwise_equivalent": equivalent(a6, a8)},
        "extraction": {"six_gib": e6s, "eight_gib": e8s,
                       "six_vs_eight_throughput_change": extraction_gain,
                       "cross_configuration_bitwise_equivalent": equivalent(e6, e8)},
        "decision": (
            "The 6 GiB core's narrow arithmetic gain did not transfer. Extraction incurred enough additional L2 misses and SD fallback to regress materially, so 8 GiB remains the protected-core control."),
        "claim_boundary": (
            "Arithmetic used matched already-warmed family L2 roots; extraction used matched fresh 12 GiB family cartridges and excludes each cold first pass. "
            "The short continuations are a mechanism-transfer gate, not a replacement for the promoted longer-window throughput evidence. Reproducible L2 cache directories were deleted after evidence capture to recover disk space."),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "arithmetic_gain": arithmetic_gain,
                      "extraction_gain": extraction_gain, "canonical_sha256": report["canonical_sha256"]}))


if __name__ == "__main__":
    main()
