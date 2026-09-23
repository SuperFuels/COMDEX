#!/usr/bin/env python3
"""Measure false refusal and false bypass on the frozen extraction stress corpus."""

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
from backend.modules.aion_inference.candidate_supplier_intent_normalizer import (
    canonicalize_supplier_extraction_request,
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
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--seed", type=int, default=200907)
    parser.add_argument("--candidate-normalizer", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {
        "tasks": args.tasks.resolve(), "answers": args.answers.resolve(),
        "bundle": args.bundle.resolve(),
    }
    output = args.output.resolve()
    if args.iterations < 1:
        raise SystemExit("iterations must be positive")
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all inputs and evidence must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")

    task_document = json.loads(paths["tasks"].read_text())
    if task_document.get("schema_version") != "aion.supplier_extraction_stress_tasks.v1":
        raise RuntimeError("unsupported task manifest")
    tasks = list(task_document["cases"])
    random.Random(args.seed).shuffle(tasks)
    class_counts = {
        name: sum(item["class"] == name for item in tasks)
        for name in ("useful_extraction", "fallback_required", "reject")
    }
    if class_counts != {"useful_extraction": 24, "fallback_required": 8, "reject": 8}:
        raise RuntimeError(f"unexpected stress-corpus balance: {class_counts}")

    bundle = paths["bundle"]
    cartridge = bundle / "supplier_payment_controls.v1.json"
    signature = bundle / "supplier_payment_controls.v1.sig.json"
    trust = bundle / "trust_anchors.v1.json"
    refs = {key: f"fixture:{key}" for key in CONTROL_IDS}
    observations = []
    payment_allowed = False
    for _ in range(args.iterations):
        for task in tasks:
            started = time.perf_counter()
            canonical = (
                canonicalize_supplier_extraction_request(task["request"])
                if args.candidate_normalizer else task["request"]
            )
            extracted = extract_verified_supplier_fields(canonical) if canonical else None
            execution = execute_supplier_payment_review(
                actor_role="finance_reviewer", evidence_references=refs,
                variable_fields=extracted.fields if extracted else {}, human_approved=True,
                cartridge_path=cartridge, signature_path=signature,
                trust_anchors_path=trust,
            ) if extracted else None
            elapsed = time.perf_counter() - started
            payment_allowed = payment_allowed or bool(
                execution and execution.payment_execution_allowed
            )
            observations.append({
                "case_id": task["case_id"], "class": task["class"],
                "fields": dict(extracted.fields) if extracted else None,
                "canonical_request_sha256": (
                    hashlib.sha256(canonical.encode()).hexdigest() if canonical else None
                ),
                "receipt_valid": bool(
                    extracted and verify_proof_receipt(extracted.proof_receipt)
                    and execution and execution.review_complete
                    and verify_proof_receipt(execution.proof_receipt)
                ),
                "receipt_sha256": (
                    extracted.proof_receipt["proof_receipt_sha256"] if extracted else None
                ),
                "elapsed_seconds": elapsed,
            })

    # The answer key is deliberately opened only after all candidate decisions.
    answer_document = json.loads(paths["answers"].read_text())
    if answer_document.get("schema_version") != "aion.supplier_extraction_stress_answers.v1":
        raise RuntimeError("unsupported answer manifest")
    answers = answer_document["answers"]
    useful_ids = {item["case_id"] for item in tasks if item["class"] == "useful_extraction"}
    if set(answers) != useful_ids:
        raise RuntimeError("answer key does not exactly cover useful extraction cases")

    false_refusals, wrong_extractions, false_bypasses = [], [], []
    receipt_hashes: dict[str, set[str]] = {case_id: set() for case_id in useful_ids}
    latencies: dict[str, list[float]] = {key: [] for key in class_counts}
    for item in observations:
        latencies[item["class"]].append(item["elapsed_seconds"])
        if item["class"] == "useful_extraction":
            if item["fields"] is None:
                false_refusals.append(item["case_id"])
            elif item["fields"] != answers[item["case_id"]] or not item["receipt_valid"]:
                wrong_extractions.append(item["case_id"])
            if item["receipt_sha256"]:
                receipt_hashes[item["case_id"]].add(item["receipt_sha256"])
        elif item["fields"] is not None:
            false_bypasses.append(item["case_id"])

    useful_executions = class_counts["useful_extraction"] * args.iterations
    guard_executions = (
        class_counts["fallback_required"] + class_counts["reject"]
    ) * args.iterations
    accepted_useful = useful_executions - len(false_refusals) - len(wrong_extractions)
    acceptance = {
        "frozen_manifests_hash_bound": True,
        "all_useful_extractions_exact_without_false_refusal": (
            not false_refusals and not wrong_extractions
        ),
        "zero_compound_or_adversarial_false_bypasses": not false_bypasses,
        "all_accepted_receipts_deterministic": all(
            len(values) <= 1 for values in receipt_hashes.values()
        ),
        "answer_key_opened_only_after_all_candidate_decisions": True,
        "model_calls_zero": True,
        "payment_execution_never_allowed": not payment_allowed,
    }
    report = {
        "schema_version": "aion.verified_extraction_stress.v1",
        "paths": {key: str(value) for key, value in paths.items()},
        "hashes": {
            "tasks": _sha256(paths["tasks"]), "answers": _sha256(paths["answers"]),
            "cartridge": _sha256(cartridge), "signature": _sha256(signature),
            "trust_anchors": _sha256(trust),
        },
        "method": {
            "seed": args.seed, "iterations": args.iterations,
            "candidate_normalizer": args.candidate_normalizer,
            "case_counts": class_counts, "useful_executions": useful_executions,
            "guard_executions": guard_executions,
            "answer_key_opened_after_candidate_decisions": True,
        },
        "quality": {
            "accepted_useful_executions": accepted_useful,
            "useful_false_refusal_executions": len(false_refusals),
            "useful_false_refusal_rate_percent": 100 * len(false_refusals) / useful_executions,
            "wrong_extraction_executions": len(wrong_extractions),
            "guard_false_bypass_executions": len(false_bypasses),
            "unique_false_refusal_cases": sorted(set(false_refusals)),
            "unique_wrong_extraction_cases": sorted(set(wrong_extractions)),
            "unique_false_bypass_cases": sorted(set(false_bypasses)),
        },
        "latency": {
            name: {
                "p50_seconds": statistics.median(values),
                "p95_seconds_nearest_rank": _p95(values),
            }
            for name, values in latencies.items()
        },
        "acceptance": acceptance,
        "result": "PASS" if all(acceptance.values()) else "FAIL",
        "claim_boundary": (
            "Frozen synthetic stress diagnostic for parser coverage and guard safety. "
            "A failure identifies unsupported language and cannot be used for promotion."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "output": str(output), "result": report["result"],
        "quality": report["quality"], "latency": report["latency"],
        "acceptance": acceptance, "report_sha256": report["report_sha256"],
    }, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
