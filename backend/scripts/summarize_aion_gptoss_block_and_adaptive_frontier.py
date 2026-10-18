#!/usr/bin/env python3
"""Create a compact, hash-bound summary of exact-block and adaptive-k results."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path


def canonical(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def source(path: Path) -> tuple[dict, dict]:
    value = json.loads(path.read_text())
    return value, {
        "path": str(path.resolve()),
        "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "canonical_sha256": value.get("canonical_sha256"),
    }


def continuation_summary(runtime: dict) -> dict:
    prompt = len(runtime["input_token_ids"])
    runs = [runtime["run_a"], runtime["run_b"], *runtime.get("additional_runs", [])]
    summaries = []
    for run in runs:
        tokens = run["tokens"][prompt:]
        seconds = [token["wall_seconds"] for token in tokens]
        active = collections.Counter(
            len(layer["route"]) for token in tokens for layer in token["layers"])
        summaries.append({
            "positions": len(tokens),
            "tokens_per_second": len(tokens) / sum(seconds),
            "p50_token_seconds": statistics.median(seconds),
            "p95_token_seconds": sorted(seconds)[int(.95 * (len(seconds) - 1))],
            "active_expert_layer_counts": dict(sorted(active.items())),
            "expert_load_seconds": sum(
                layer["expert_load_seconds"] for token in tokens for layer in token["layers"]),
            "all_routes_in_pool": all(
                layer["route_pool_complete"] for token in tokens for layer in token["layers"]),
        })
    warm = summaries[1:]
    return {
        "passes": summaries,
        "post_warmup_tokens_per_second_p50": statistics.median(
            item["tokens_per_second"] for item in warm),
        "post_warmup_p50_token_seconds_p50": statistics.median(
            item["p50_token_seconds"] for item in warm),
        "post_warmup_p95_token_seconds_p50": statistics.median(
            item["p95_token_seconds"] for item in warm),
        "internally_bitwise_repeatable": runtime["final_hidden_and_logits_bitwise_repeatable"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--block", type=Path, action="append", required=True)
    parser.add_argument("--candidate", type=Path, action="append", required=True)
    parser.add_argument("--receipt", type=Path, action="append", required=True)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    if len(args.candidate) != len(args.receipt):
        raise SystemExit("each candidate requires one receipt")

    blocks = []
    block_sources = []
    for path in args.block:
        value, evidence = source(path)
        blocks.append({
            "positions": value["positions"],
            "status": value["status"],
            "wall_speedup_p50": value["wall_speedup_p50"],
            "compressed_traffic_reduction_p50": value["compressed_traffic_reduction_p50"],
            "all_positions_bitwise_exact": value["all_positions_all_runs_bitwise_exact"],
            "peak_live_expert_bytes": value["peak_live_expert_bytes"],
            "exploratory_pair_only": value.get("exploratory_pair_only", False),
        })
        block_sources.append(evidence)

    candidates = []
    candidate_sources = []
    for runtime_path, receipt_path in zip(args.candidate, args.receipt, strict=True):
        runtime, runtime_source = source(runtime_path)
        receipt, receipt_source = source(receipt_path)
        summary = continuation_summary(runtime)
        summary.update({
            "continuation_active_experts": runtime.get("continuation_active_experts"),
            "gate_mass_threshold": runtime.get("continuation_gate_mass_threshold"),
            "preserve_dropped_gate_mass": runtime.get("preserve_dropped_gate_mass", False),
            "generated_text": receipt["generated_text"],
            "contains_expected_391": "391" in receipt["generated_text"],
            "receipt_passed": receipt["status"] == "PASSED",
        })
        candidates.append(summary)
        candidate_sources.append({"runtime": runtime_source, "receipt": receipt_source})

    control, control_source = source(args.control)
    control_rates = [candidate["tokens_per_second"] for candidate in control["candidates"]
                     if candidate["capacity_gib"] == 8.0 for candidate in candidate["passes"]]
    report = {
        "schema": "aion.gptoss-120b-block-and-adaptive-frontier.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "exact_block": {
            "decision": "STOP_AS_PRIMARY_SPEED_STRATEGY",
            "runs": blocks,
            "maximum_wall_speedup": max(item["wall_speedup_p50"] for item in blocks),
            "maximum_traffic_reduction": max(
                item["compressed_traffic_reduction_p50"] for item in blocks),
            "reason": "macOS page caching already removes much repeated physical SD traffic; logical byte reduction did not transfer to wall time",
        },
        "adaptive_experts": {
            "decision": "RETAIN_075_PRESERVED_MASS_FOR_BROADER_QUALITY_NOT_SPEED_PROMOTION",
            "candidates": candidates,
        },
        "promoted_narrow_control": {
            "architecture": "exact unrestricted prefill plus protected 8 GiB four-expert continuation",
            "tokens_per_second": control_rates,
            "tokens_per_second_p50": statistics.median(control_rates),
            "status": control["status"],
        },
        "sources": {
            "blocks": block_sources,
            "adaptive_candidates": candidate_sources,
            "control": control_source,
        },
        "claim_boundary": (
            "The exact block tests execute all 36 layers and full logits against frozen teacher "
            "traces, but do not include draft cost or free-running acceptance. Adaptive expert "
            "runs are changed-model quality tracks using original GPT-OSS 120B weights; they are "
            "not bit-exact unrestricted GPT-OSS 120B. Arithmetic success does not establish broad quality."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "exact_block_decision": report["exact_block"]["decision"],
        "maximum_exact_block_wall_speedup": report["exact_block"]["maximum_wall_speedup"],
        "adaptive_decision": report["adaptive_experts"]["decision"],
        "promoted_control_tps_p50": report["promoted_narrow_control"]["tokens_per_second_p50"],
        "canonical_sha256": report["canonical_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
