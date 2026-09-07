#!/usr/bin/env python3
"""Measure the verified supplier-extraction AtomSheet on its derivation cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
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
    parser.add_argument("--original-manifest", type=Path, required=True)
    parser.add_argument("--holdout-tasks", type=Path, required=True)
    parser.add_argument("--holdout-answers", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"original_manifest": args.original_manifest.resolve(),
             "holdout_tasks": args.holdout_tasks.resolve(),
             "holdout_answers": args.holdout_answers.resolve(),
             "bundle": args.bundle.resolve()}
    output = args.output.resolve()
    if args.iterations < 1: raise SystemExit("iterations must be positive")
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all inputs and evidence must remain on external storage")
    if output.exists(): raise SystemExit(f"refusing to overwrite evidence: {output}")
    original = json.loads(paths["original_manifest"].read_text())
    tasks = json.loads(paths["holdout_tasks"].read_text())["cases"]
    answers = json.loads(paths["holdout_answers"].read_text())["answers"]
    valid = [{"case_id": item["case_id"], "request": item["request"],
              "expected": item["expected"]} for item in original["cases"]]
    valid.extend({"case_id": item["case_id"], "request": item["request"],
                  "expected": answers[item["case_id"]]} for item in tasks
                 if item["family"] == "extraction" and item["expected_disposition"] == "complete")
    invalid = [item for item in tasks if item["family"] == "extraction"
               and item["expected_disposition"] != "complete"]
    if len(valid) != 12 or len(invalid) != 4:
        raise RuntimeError("expected twelve valid and four invalid derivation cases")
    bundle = paths["bundle"]
    cartridge = bundle / "supplier_payment_controls.v1.json"
    signature = bundle / "supplier_payment_controls.v1.sig.json"
    trust = bundle / "trust_anchors.v1.json"
    refs = {key: f"fixture:{key}" for key in CONTROL_IDS}
    elapsed, valid_failures, false_bypasses, receipt_hashes = [], [], [], {}
    payment_allowed = False
    for _ in range(args.iterations):
        for case in valid:
            started = time.perf_counter()
            extracted = extract_verified_supplier_fields(case["request"])
            execution = execute_supplier_payment_review(
                actor_role="finance_reviewer", evidence_references=refs,
                variable_fields=extracted.fields if extracted else {}, human_approved=True,
                cartridge_path=cartridge, signature_path=signature, trust_anchors_path=trust,
            ) if extracted else None
            elapsed.append(time.perf_counter() - started)
            passed = bool(extracted and dict(extracted.fields) == case["expected"]
                          and verify_proof_receipt(extracted.proof_receipt)
                          and execution and execution.review_complete
                          and verify_proof_receipt(execution.proof_receipt)
                          and not execution.payment_execution_allowed)
            if not passed: valid_failures.append(case["case_id"])
            if extracted:
                receipt_hashes.setdefault(case["case_id"], set()).add(
                    extracted.proof_receipt["proof_receipt_sha256"]
                )
            payment_allowed = payment_allowed or bool(
                execution and execution.payment_execution_allowed
            )
        for case in invalid:
            started = time.perf_counter()
            extracted = extract_verified_supplier_fields(case["request"])
            elapsed.append(time.perf_counter() - started)
            if extracted is not None: false_bypasses.append(case["case_id"])
    acceptance = {
        "all_12000_valid_extractions_and_reviews_exact": not valid_failures,
        "zero_4000_invalid_false_bypasses": not false_bypasses,
        "all_extraction_receipts_deterministic": all(
            len(values) == 1 for values in receipt_hashes.values()
        ) and len(receipt_hashes) == 12,
        "model_calls_zero": True,
        "payment_execution_never_allowed": not payment_allowed,
    }
    report = {"schema_version": "aion.verified_extraction_training_gate.v1",
              "paths": {key: str(value) for key, value in paths.items()},
              "hashes": {"original_manifest": _sha256(paths["original_manifest"]),
                         "holdout_tasks": _sha256(paths["holdout_tasks"]),
                         "holdout_answers": _sha256(paths["holdout_answers"]),
                         "cartridge": _sha256(cartridge), "signature": _sha256(signature),
                         "trust_anchors": _sha256(trust)},
              "method": {"iterations": args.iterations, "valid_cases": 12,
                         "invalid_cases": 4, "valid_executions": 12 * args.iterations,
                         "invalid_executions": 4 * args.iterations,
                         "cohort_role": "derivation_and_training_gate_not_unseen_holdout"},
              "latency": {"median_seconds": statistics.median(elapsed),
                          "p95_seconds_nearest_rank": _p95(elapsed),
                          "minimum_seconds": min(elapsed), "maximum_seconds": max(elapsed)},
              "failures": {"valid": sorted(set(valid_failures)),
                           "invalid_false_bypasses": sorted(set(false_bypasses))},
              "acceptance": acceptance, "result": "PASS" if all(acceptance.values()) else "FAIL",
              "claim_boundary": (
                  "This is the exact twelve-case derivation cohort and four known attacks, not an "
                  "unseen generalization test. Fixture evidence does not authenticate real suppliers."
              )}
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "result": report["result"],
                      "latency": report["latency"], "acceptance": acceptance,
                      "report_sha256": report["report_sha256"]}, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
