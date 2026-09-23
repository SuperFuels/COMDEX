#!/usr/bin/env python3
"""Bind live trajectory interruption to a deterministic AtomSheet repair."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time
from typing import Any

from backend.modules.aion_inference.trajectory_verification_ladder import (
    deterministic_entailment_answer,
    earliest_failure,
)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_verified(path: Path) -> dict:
    value = json.loads(path.read_text())
    claimed = value.get("canonical_sha256")
    body = dict(value)
    body.pop("canonical_sha256", None)
    if claimed != canonical_sha256(body):
        raise ValueError(f"canonical hash failed: {path}")
    return value


def response_tokens(report: dict, run_name: str) -> list[int]:
    offset = int(report["prompt_token_count"]) - 1
    return [int(item["generated_token_id"]) for item in report[run_name]["tokens"][offset:]]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-guard-report", type=Path, required=True)
    parser.add_argument("--full-failed-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    live = load_verified(args.live_guard_report)
    receipt = load_verified(args.full_failed_receipt)
    live_a = response_tokens(live, "run_a")
    live_b = response_tokens(live, "run_b")
    full = [int(value) for value in receipt["generated_token_ids"]]
    failure = earliest_failure(live_a)
    timings = []
    repaired = None
    for _ in range(1000):
        started = time.perf_counter_ns()
        repaired = deterministic_entailment_answer(receipt["prompt"])
        timings.append(time.perf_counter_ns() - started)
    acceptance = {
        "live_execution_passed": live.get("status") == "PASSED",
        "live_routes_hidden_logits_repeatable": (
            live.get("routes_repeatable") is True
            and live.get("final_hidden_and_logits_bitwise_repeatable") is True
        ),
        "guard_enabled": live.get("trajectory_loop_guard") is True,
        "both_passes_escalated": all(
            item.get("decision") == "ESCALATE"
            for item in live.get("trajectory_guard_runs", [])
        ) and len(live.get("trajectory_guard_runs", [])) == 2,
        "interrupted_trajectories_identical": live_a == live_b,
        "interrupted_trajectory_matches_authentic_failed_prefix": full[:len(live_a)] == live_a,
        "interrupted_before_failed_completion": 0 < len(live_a) < len(full),
        "streaming_detector_reproduces_live_stop": (
            failure is not None and failure.first_detected_token == len(live_a)
        ),
        "deterministic_repair_available": repaired is not None,
        "deterministic_repair_states_derived_conclusion": (
            repaired is not None and "this box is heavy" in repaired.lower()
        ),
        "repair_median_under_one_millisecond": statistics.median(timings) < 1_000_000,
    }
    result = {
        "schema": "aion.gptoss-120b-live-guarded-atomsheet-repair.v1",
        "status": "PASSED" if all(acceptance.values()) else "FAILED",
        "quality_track": True,
        "prompt": receipt["prompt"],
        "repaired_answer": repaired,
        "live_generated_tokens_before_interruption": len(live_a),
        "original_failed_generated_tokens": len(full),
        "failed_tokens_avoided": len(full) - len(live_a),
        "failed_generation_work_reduction_percent": 100.0 * (1.0 - len(live_a) / len(full)),
        "failure": ({
            "kind": failure.kind,
            "first_detected_token": failure.first_detected_token,
            "detail": failure.detail,
        } if failure is not None else None),
        "repair_median_microseconds": statistics.median(timings) / 1000.0,
        "repair_p95_microseconds": sorted(timings)[949] / 1000.0,
        "acceptance": acceptance,
        "hashes": {
            "live_guard_report_file_sha256": file_sha256(args.live_guard_report),
            "live_guard_report_canonical_sha256": live["canonical_sha256"],
            "full_failed_receipt_file_sha256": file_sha256(args.full_failed_receipt),
            "full_failed_receipt_canonical_sha256": receipt["canonical_sha256"],
        },
        "claim_boundary": (
            "One authentic failed 120B quality-track trajectory was interrupted live and repaired "
            "by a deterministic proof over an explicitly supported syllogism grammar. This is a "
            "verified completed-task result and measured avoidance of known-bad generation work. "
            "It is not general semantic verification, unrestricted 120B equivalence, or a new "
            "model tokens-per-second result; unsupported prompts must use a critic or fallback."
        ),
    }
    result["canonical_sha256"] = canonical_sha256(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
