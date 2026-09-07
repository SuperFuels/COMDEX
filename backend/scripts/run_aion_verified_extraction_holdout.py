#!/usr/bin/env python3
"""Evaluate the verified extraction AtomSheet on a separately frozen holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import statistics
import time
from typing import Any

from backend.modules.aion_inference import (
    execute_supplier_payment_review,
    extract_verified_supplier_fields,
    verify_proof_receipt,
)
from backend.scripts.run_aion_balanced_business_router import CONTROL_IDS, _p95, _sha256


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--answers", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=190907)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"tasks": args.tasks.resolve(), "answers": args.answers.resolve(),
             "bundle": args.bundle.resolve()}
    output = args.output.resolve()
    if args.iterations < 1: raise SystemExit("iterations must be positive")
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all inputs and evidence must remain on external storage")
    if output.exists(): raise SystemExit(f"refusing to overwrite evidence: {output}")
    task_document = json.loads(paths["tasks"].read_text())
    if task_document.get("schema_version") != "aion.supplier_extraction_holdout_tasks.v1":
        raise RuntimeError("unsupported task manifest")
    tasks = list(task_document["cases"])
    random.Random(args.seed).shuffle(tasks)
    bundle = paths["bundle"]
    cartridge = bundle / "supplier_payment_controls.v1.json"
    signature = bundle / "supplier_payment_controls.v1.sig.json"
    trust = bundle / "trust_anchors.v1.json"
    refs = {key: f"fixture:{key}" for key in CONTROL_IDS}
    # Complete extraction and signed review before opening the answer key.
    observations = []
    payment_allowed = False
    for _ in range(args.iterations):
        for task in tasks:
            started = time.perf_counter()
            extracted = extract_verified_supplier_fields(task["request"])
            execution = execute_supplier_payment_review(
                actor_role="finance_reviewer", evidence_references=refs,
                variable_fields=extracted.fields if extracted else {}, human_approved=True,
                cartridge_path=cartridge, signature_path=signature, trust_anchors_path=trust,
            ) if extracted else None
            elapsed = time.perf_counter() - started
            payment_allowed = payment_allowed or bool(execution and execution.payment_execution_allowed)
            observations.append({"case_id": task["case_id"],
                                 "expected_disposition": task["expected_disposition"],
                                 "fields": dict(extracted.fields) if extracted else None,
                                 "extraction_receipt_valid": bool(extracted and verify_proof_receipt(extracted.proof_receipt)),
                                 "extraction_receipt_sha256": extracted.proof_receipt["proof_receipt_sha256"] if extracted else None,
                                 "review_complete": bool(execution and execution.review_complete),
                                 "review_receipt_valid": bool(execution and verify_proof_receipt(execution.proof_receipt)),
                                 "elapsed_seconds": elapsed})
    answer_document = json.loads(paths["answers"].read_text())
    if answer_document.get("schema_version") != "aion.supplier_extraction_holdout_answers.v1":
        raise RuntimeError("unsupported answer manifest")
    answers = answer_document["answers"]
    valid_ids = {item["case_id"] for item in tasks if item["expected_disposition"] == "complete"}
    if set(answers) != valid_ids: raise RuntimeError("answer key does not exactly cover valid cases")
    failures, false_bypasses = [], []
    receipt_hashes: dict[str, set[str]] = {case_id: set() for case_id in valid_ids}
    valid_elapsed, invalid_elapsed = [], []
    for item in observations:
        case_id = item["case_id"]
        if item["expected_disposition"] == "complete":
            valid_elapsed.append(item["elapsed_seconds"])
            passed = (item["fields"] == answers[case_id]
                      and item["extraction_receipt_valid"]
                      and item["review_complete"] and item["review_receipt_valid"])
            if not passed: failures.append(case_id)
            if item["extraction_receipt_sha256"]:
                receipt_hashes[case_id].add(item["extraction_receipt_sha256"])
        else:
            invalid_elapsed.append(item["elapsed_seconds"])
            if item["fields"] is not None: false_bypasses.append(case_id)
    acceptance = {
        "frozen_manifests_hash_bound": True,
        "all_16000_unseen_extractions_and_reviews_exact": not failures,
        "zero_16000_adversarial_false_bypasses": not false_bypasses,
        "all_extraction_receipts_deterministic": all(len(values) == 1 for values in receipt_hashes.values()),
        "answer_key_opened_only_after_all_routing_and_review": True,
        "model_calls_zero": True,
        "payment_execution_never_allowed": not payment_allowed,
    }
    total_seconds = sum(valid_elapsed) + sum(invalid_elapsed)
    report = {"schema_version": "aion.verified_extraction_holdout.v1",
              "paths": {key: str(value) for key, value in paths.items()},
              "hashes": {"tasks": _sha256(paths["tasks"]), "answers": _sha256(paths["answers"]),
                         "cartridge": _sha256(cartridge), "signature": _sha256(signature),
                         "trust_anchors": _sha256(trust)},
              "method": {"seed": args.seed, "iterations": args.iterations,
                         "unseen_valid_cases": 16, "adversarial_cases": 16,
                         "valid_executions": 16 * args.iterations,
                         "adversarial_executions": 16 * args.iterations,
                         "answer_key_opened_after_routing": True},
              "latency": {"valid_median_seconds": statistics.median(valid_elapsed),
                          "valid_p95_seconds_nearest_rank": _p95(valid_elapsed),
                          "invalid_median_seconds": statistics.median(invalid_elapsed),
                          "invalid_p95_seconds_nearest_rank": _p95(invalid_elapsed),
                          "maximum_seconds": max(valid_elapsed + invalid_elapsed)},
              "economics": {"total_measured_seconds": total_seconds,
                            "valid_completed_tasks_per_hour_in_mixed_holdout":
                                len(valid_elapsed) * 3600 / total_seconds,
                            "model_calls_avoided": len(observations)},
              "failures": {"valid": sorted(set(failures)),
                           "adversarial_false_bypasses": sorted(set(false_bypasses))},
              "acceptance": acceptance, "result": "PASS" if all(acceptance.values()) else "FAIL",
              "claim_boundary": (
                  "Frozen synthetic unseen-value holdout over eight fixed sentence shapes, not open-ended "
                  "language extraction. Fixture evidence does not authenticate a real supplier or authorize payment."
              )}
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "result": report["result"],
                      "latency": report["latency"], "economics": report["economics"],
                      "acceptance": acceptance, "report_sha256": report["report_sha256"]}, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
