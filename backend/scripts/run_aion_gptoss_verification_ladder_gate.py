#!/usr/bin/env python3
"""Evaluate the AION proposal-verification ladder on hash-bound receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time
from typing import Any

from backend.modules.aion_inference.trajectory_verification_ladder import (
    earliest_failure,
    verify_candidate,
)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_verified(path: Path) -> dict:
    report = json.loads(path.read_text())
    claimed = report.get("canonical_sha256")
    body = dict(report)
    body.pop("canonical_sha256", None)
    if claimed != canonical_sha256(body):
        raise ValueError(f"canonical hash failed: {path}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--failed-receipt", type=Path, required=True)
    parser.add_argument("--passing-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")

    cases = []
    for expected, path in (("ESCALATE", args.failed_receipt), ("ACCEPT", args.passing_receipt)):
        receipt = load_verified(path)
        tokens = [int(value) for value in receipt["generated_token_ids"]]
        timings = []
        decision = None
        for _ in range(1000):
            started = time.perf_counter_ns()
            decision = verify_candidate(receipt["prompt"], receipt["generated_text"], tokens)
            timings.append(time.perf_counter_ns() - started)
        assert decision is not None
        failure = earliest_failure(tokens)
        cases.append({
            "receipt": str(path.resolve()),
            "receipt_file_sha256": file_sha256(path),
            "receipt_canonical_sha256": receipt["canonical_sha256"],
            "generated_tokens": len(tokens),
            "expected_decision": expected,
            "decision": decision.to_dict(),
            "earliest_structural_failure_token": (
                failure.first_detected_token if failure is not None else None
            ),
            "tokens_avoided_if_interrupted": (
                len(tokens) - failure.first_detected_token if failure is not None else 0
            ),
            "verifier_median_microseconds": statistics.median(timings) / 1000.0,
            "verifier_p95_microseconds": sorted(timings)[949] / 1000.0,
            "passed": decision.decision == expected,
        })

    acceptance = {
        "failed_trajectory_detected": cases[0]["decision"]["decision"] == "ESCALATE",
        "failure_detected_before_completion": (
            cases[0]["earliest_structural_failure_token"] is not None
            and cases[0]["tokens_avoided_if_interrupted"] > 0
        ),
        "correct_deterministic_conclusion_accepted": cases[1]["decision"]["decision"] == "ACCEPT",
        "passing_trajectory_has_no_structural_failure": (
            cases[1]["earliest_structural_failure_token"] is None
        ),
        "verifier_median_under_one_millisecond": max(
            item["verifier_median_microseconds"] for item in cases
        ) < 1000.0,
    }
    result = {
        "schema": "aion.gptoss-120b-proposal-verification-ladder.v1",
        "status": "PASSED" if all(acceptance.values()) else "FAILED",
        "quality_track": True,
        "cases": cases,
        "acceptance": acceptance,
        "claim_boundary": (
            "Offline replay of two authentic 120B receipt trajectories. This establishes cheap "
            "early rejection of the known looping proposal and deterministic acceptance of the "
            "known correct syllogism. It does not yet establish live rollback, broad semantic "
            "coverage, or a new end-to-end tokens-per-second result."
        ),
    }
    result["canonical_sha256"] = canonical_sha256(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
