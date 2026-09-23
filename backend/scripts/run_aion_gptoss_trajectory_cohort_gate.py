#!/usr/bin/env python3
"""Freeze a hash-bound cohort for the token-trajectory rejection guard."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from backend.modules.aion_inference.trajectory_verification_ladder import earliest_failure


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode()).hexdigest()


def load_verified(path: Path) -> dict:
    value = json.loads(path.read_text())
    claimed = value.get("canonical_sha256")
    body = dict(value)
    body.pop("canonical_sha256", None)
    if claimed != canonical_sha256(body):
        raise ValueError(f"canonical hash failed: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--healthy", type=Path, action="append", default=[])
    parser.add_argument("--failed", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing to overwrite evidence")
    if not args.healthy or not args.failed:
        raise SystemExit("at least one healthy and one failed receipt are required")
    cases = []
    for expected, paths in (("CONTINUE", args.healthy), ("ESCALATE", args.failed)):
        for path in paths:
            receipt = load_verified(path)
            tokens = [int(value) for value in receipt["generated_token_ids"]]
            failure = earliest_failure(tokens)
            observed = "ESCALATE" if failure is not None else "CONTINUE"
            cases.append({
                "path": str(path.resolve()),
                "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "canonical_sha256": receipt["canonical_sha256"],
                "prompt": receipt.get("prompt"),
                "generated_tokens": len(tokens),
                "expected": expected,
                "observed": observed,
                "passed": expected == observed,
                "failure": ({
                    "kind": failure.kind,
                    "first_detected_token": failure.first_detected_token,
                    "detail": failure.detail,
                } if failure is not None else None),
            })
    healthy = [item for item in cases if item["expected"] == "CONTINUE"]
    failed = [item for item in cases if item["expected"] == "ESCALATE"]
    acceptance = {
        "all_receipt_hashes_valid": True,
        "zero_observed_false_positive_structural_interruptions": all(
            item["passed"] for item in healthy
        ),
        "all_declared_structural_failures_detected": all(item["passed"] for item in failed),
    }
    result = {
        "schema": "aion.gptoss-120b-trajectory-guard-cohort.v1",
        "status": "PASSED" if all(acceptance.values()) else "FAILED",
        "cases": cases,
        "healthy_cases": len(healthy),
        "failed_cases": len(failed),
        "acceptance": acceptance,
        "claim_boundary": (
            "Frozen replay of manually classified authentic receipts. This measures structural "
            "loop detection only; a CONTINUE decision does not certify semantic correctness. "
            "Broader blinded families remain required before production promotion."
        ),
    }
    result["canonical_sha256"] = canonical_sha256(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
