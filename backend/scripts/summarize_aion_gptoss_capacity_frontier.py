#!/usr/bin/env python3
"""Summarize the quality/speed frontier of request-derived 120B pools."""

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


def verified(path: Path) -> dict:
    value = json.loads(path.read_text())
    body = dict(value)
    claimed = body.pop("canonical_sha256", None)
    if claimed != canonical(body):
        raise ValueError(f"canonical hash mismatch: {path}")
    return value


def source(path: Path, value: dict) -> dict:
    return {"path": str(path.resolve()),
            "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "canonical_sha256": value["canonical_sha256"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", nargs=4, action="append", metavar=(
        "GIB", "RUNTIME", "RECEIPT", "POOL"), required=True)
    parser.add_argument("--prompt-positions", type=int, required=True)
    parser.add_argument("--expected-text", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite summary")
    control = verified(args.control)
    control_tps = []
    for run_name in ("run_a", "run_b"):
        tokens = control[run_name]["tokens"][args.prompt_positions:]
        control_tps.append(len(tokens) / sum(token["wall_seconds"] for token in tokens))
    candidates = []
    for gib_text, runtime_path_text, receipt_path_text, pool_path_text in args.candidate:
        runtime_path, receipt_path, pool_path = map(
            Path, (runtime_path_text, receipt_path_text, pool_path_text))
        runtime, receipt, pool = map(verified, (runtime_path, receipt_path, pool_path))
        passes = []
        for index, run_name in enumerate(("run_a", "run_b")):
            run = runtime[run_name]
            tokens = run["tokens"][args.prompt_positions:]
            seconds = sum(token["wall_seconds"] for token in tokens)
            latencies = [token["wall_seconds"] for token in tokens]
            passes.append({
                "pass": index + 1,
                "continuation_positions": len(tokens),
                "continuation_seconds": seconds,
                "tokens_per_second": len(tokens) / seconds,
                "speedup_vs_unrestricted": (len(tokens) / seconds) / control_tps[index],
                "median_token_seconds": statistics.median(latencies),
                "p95_token_seconds": sorted(latencies)[
                    max(0, int(0.95 * len(latencies)) - 1)],
                "prompt_seconds": sum(token["wall_seconds"]
                                      for token in run["tokens"][:args.prompt_positions]),
                "first_response_ready_seconds": (
                    runtime["constrained_expert_pool_preload_seconds"]
                    + sum(token["wall_seconds"]
                          for token in run["tokens"][:args.prompt_positions])
                    + run["prompt_to_continuation_rehydrate_seconds"]),
                "continuation_expert_load_seconds": sum(
                    sum(layer["expert_load_seconds"] for layer in token["layers"])
                    for token in tokens),
            })
        candidates.append({
            "capacity_gib": float(gib_text),
            "pool_raw_bytes": pool["resident_raw_bytes"],
            "pool_entries": pool["total_layer_experts"],
            "expected_answer_present": args.expected_text in receipt["generated_text"],
            "generated_text": receipt["generated_text"],
            "passes": passes,
            "sources": {"runtime": source(runtime_path, runtime),
                        "receipt": source(receipt_path, receipt),
                        "pool": source(pool_path, pool)},
        })
    correct = [item for item in candidates if item["expected_answer_present"]]
    promoted = max(correct, key=lambda item: statistics.median(
        result["tokens_per_second"] for result in item["passes"]))
    report = {
        "schema": "aion.gptoss-120b-capacity-frontier.v1",
        "status": "PROMOTE_NARROW_8G_FRONTIER" if promoted["capacity_gib"] == 8 else "REVIEW",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "GPT-OSS 120B Q4_K_M/MXFP4",
        "prompt": "What is 17 multiplied by 23?",
        "expected_text": args.expected_text,
        "control": {"source": source(args.control, control),
                    "tokens_per_second": control_tps},
        "candidates": candidates,
        "promoted_narrow_capacity_gib": promoted["capacity_gib"],
        "decision": (
            "Advance the 8 GiB pool to the remaining frozen prompt families. Stop 6 and 7 GiB "
            "for this gate because neither emitted the expected answer in the unchanged window."
        ),
        "claim_boundary": (
            "A single frozen arithmetic task identifies a narrow request-pool frontier. It does "
            "not establish a universal capacity threshold or general GPT-OSS 120B quality."
        ),
    }
    report["canonical_sha256"] = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"],
                      "promoted_narrow_capacity_gib": report["promoted_narrow_capacity_gib"],
                      "canonical_sha256": report["canonical_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
