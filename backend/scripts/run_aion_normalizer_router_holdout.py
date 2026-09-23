#!/usr/bin/env python3
"""Evaluate the promoted supplier normalizer through the governed router."""

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
    AdaptiveInferenceRuntime,
    GovernedBusinessRouter,
    LearnedAtomSheetStore,
    verify_proof_receipt,
    verify_trace_chain,
)
from backend.scripts.run_aion_balanced_business_router import _p95, _sha256


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
    parser.add_argument("--learning-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--seed", type=int, default=709207)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {
        "tasks": args.tasks.resolve(), "answers": args.answers.resolve(),
        "bundle": args.bundle.resolve(), "learning_root": args.learning_root.resolve(),
    }
    output = args.output.resolve()
    if args.iterations < 1:
        raise SystemExit("iterations must be positive")
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all inputs, state and evidence must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")

    task_document = json.loads(paths["tasks"].read_text())
    if task_document.get("schema_version") != "aion.supplier_extraction_stress_tasks.v1":
        raise RuntimeError("unsupported task manifest")
    tasks = list(task_document["cases"])
    random.Random(args.seed).shuffle(tasks)
    runtime_root = root / "runtime-evidence" / args.run_id
    trace_path = runtime_root / "trace.jsonl"
    router = GovernedBusinessRouter(
        runtime=AdaptiveInferenceRuntime(
            replay_path=runtime_root / "replay.sqlite3", trace_path=trace_path,
            learned_store=LearnedAtomSheetStore(
                paths["learning_root"] / "learning.sqlite3",
                paths["learning_root"] / "promoted",
            ),
        ),
        cartridge_path=paths["bundle"] / "supplier_payment_controls.v1.json",
        signature_path=paths["bundle"] / "supplier_payment_controls.v1.sig.json",
        trust_anchors_path=paths["bundle"] / "trust_anchors.v1.json",
    )

    observations = []
    for _ in range(args.iterations):
        for task in tasks:
            started = time.perf_counter()
            outcome = router.route(task["request"])
            observations.append({
                "case_id": task["case_id"], "class": task["class"],
                "route": outcome.route,
                "model_call_required": outcome.model_call_required,
                "task_completed": outcome.task_completed,
                "answer": outcome.answer,
                "receipt_valid": verify_proof_receipt(outcome.proof_receipt),
                "normalization_applied": outcome.proof_receipt.get(
                    "normalization_applied", False
                ),
                "original_request_sha256": hashlib.sha256(
                    task["request"].encode()
                ).hexdigest(),
                "receipt_request_sha256": outcome.proof_receipt.get("request_sha256"),
                "canonical_request_sha256": outcome.proof_receipt.get(
                    "canonical_request_sha256"
                ),
                "payment_execution_allowed": outcome.proof_receipt.get(
                    "payment_execution_allowed", False
                ),
                "elapsed_seconds": time.perf_counter() - started,
            })

    # Open the answer key only after every route decision has been recorded.
    answer_document = json.loads(paths["answers"].read_text())
    if answer_document.get("schema_version") != "aion.supplier_extraction_stress_answers.v1":
        raise RuntimeError("unsupported answer manifest")
    answers = answer_document["answers"]
    useful_ids = {item["case_id"] for item in tasks if item["class"] == "useful_extraction"}
    if set(answers) != useful_ids:
        raise RuntimeError("answer key does not exactly cover useful cases")

    failures = []
    useful_latencies, guard_latencies = [], []
    for item in observations:
        if item["original_request_sha256"] != item["receipt_request_sha256"]:
            failures.append((item["case_id"], "original_hash_not_bound"))
        if not item["receipt_valid"]:
            failures.append((item["case_id"], "invalid_route_receipt"))
        if item["payment_execution_allowed"]:
            failures.append((item["case_id"], "payment_authority_granted"))
        if item["class"] == "useful_extraction":
            useful_latencies.append(item["elapsed_seconds"])
            try:
                parsed = json.loads(item["answer"] or "")
            except json.JSONDecodeError:
                parsed = None
            if (
                item["route"] != "verified_supplier_extraction_atomsheet"
                or item["model_call_required"] or not item["task_completed"]
                or parsed != answers[item["case_id"]]
                or not item["canonical_request_sha256"]
            ):
                failures.append((item["case_id"], "useful_route_failed"))
        else:
            guard_latencies.append(item["elapsed_seconds"])
            if item["route"] == "verified_supplier_extraction_atomsheet":
                failures.append((item["case_id"], "guard_false_bypass"))

    class_counts = {
        name: sum(item["class"] == name for item in tasks)
        for name in ("useful_extraction", "fallback_required", "reject")
    }
    acceptance = {
        "all_useful_tasks_completed_exactly": not any(
            reason == "useful_route_failed" for _, reason in failures
        ),
        "zero_guard_false_bypasses": not any(
            reason == "guard_false_bypass" for _, reason in failures
        ),
        "all_original_and_canonical_hashes_bound": not any(
            reason == "original_hash_not_bound" for _, reason in failures
        ),
        "all_route_receipts_valid": not any(
            reason == "invalid_route_receipt" for _, reason in failures
        ),
        "payment_execution_never_allowed": not any(
            reason == "payment_authority_granted" for _, reason in failures
        ),
        "answer_key_opened_only_after_all_routes": True,
        "trace_chain_valid": verify_trace_chain(trace_path),
    }
    report = {
        "schema_version": "aion.normalizer_router_holdout.v1",
        "run_id": args.run_id,
        "paths": {key: str(value) for key, value in paths.items()},
        "hashes": {
            "tasks": _sha256(paths["tasks"]), "answers": _sha256(paths["answers"]),
            "cartridge": _sha256(paths["bundle"] / "supplier_payment_controls.v1.json"),
            "signature": _sha256(paths["bundle"] / "supplier_payment_controls.v1.sig.json"),
            "trust_anchors": _sha256(paths["bundle"] / "trust_anchors.v1.json"),
        },
        "method": {
            "iterations": args.iterations, "seed": args.seed,
            "case_counts": class_counts,
            "route_received_request_text_only": True,
            "answer_key_opened_after_all_route_decisions": True,
            "model_fallbacks_declared_but_not_executed": True,
        },
        "quality": {
            "useful_executions": class_counts["useful_extraction"] * args.iterations,
            "guard_executions": (
                class_counts["fallback_required"] + class_counts["reject"]
            ) * args.iterations,
            "failures": sorted(set(failures)),
        },
        "latency": {
            "useful_p50_seconds": statistics.median(useful_latencies),
            "useful_p95_seconds_nearest_rank": _p95(useful_latencies),
            "guard_p50_seconds": statistics.median(guard_latencies),
            "guard_p95_seconds_nearest_rank": _p95(guard_latencies),
        },
        "acceptance": acceptance,
        "result": "PASS" if all(acceptance.values()) else "FAIL",
        "claim_boundary": (
            "End-to-end governed-router validation over a finite synthetic normalizer "
            "holdout. Fallback model calls were declared but deliberately not executed."
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
