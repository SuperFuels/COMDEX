#!/usr/bin/env python3
"""Evaluate the frozen balanced holdout without exposing its answer key to routing."""

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
    execute_supplier_payment_review,
    verify_proof_receipt,
    verify_trace_chain,
)
from backend.scripts.run_aion_balanced_business_router import (
    CODE_SCHEMA,
    CONTROL_IDS,
    DRAFT_SCHEMA,
    EXTRACTION_SCHEMA,
    PLAN_SCHEMA,
    _canonical_sha256,
    _normalize_extraction,
    _p95,
    _post,
    _safe_arithmetic,
    _sha256,
)


VERIFIED_ROUTES = {
    "verified_atomsheet", "verified_replay", "verified_quotation_atomsheet",
    "verified_business_map_policy",
}


def _evaluate_model_task(
    *, task: dict[str, Any], expected: dict[str, Any], model: str, base_url: str,
    call_number: int, cartridge: Path, signature: Path, trust: Path,
) -> tuple[bool, dict[str, Any], Any]:
    family = task["family"]
    if family == "extraction":
        schema = EXTRACTION_SCHEMA
        prompt = (
            "Extract the three fields exactly as written. Do not infer, calculate, or add text.\n"
            f"REQUEST: {task['request']}"
        )
    elif family == "drafting":
        schema, prompt = DRAFT_SCHEMA, "Return JSON only. " + task["request"]
    elif family == "planning":
        schema, prompt = PLAN_SCHEMA, "Return JSON only. " + task["request"]
    elif family == "coding":
        schema, prompt = CODE_SCHEMA, "Return JSON only. " + task["request"]
    else:
        raise RuntimeError(f"no bounded executor for model family: {family}")
    event, wall_seconds = _post(base_url, {
        "model": model, "prompt": prompt, "stream": False, "think": False,
        "format": schema, "keep_alive": "10m",
        "options": {"temperature": 0, "seed": 0, "num_predict": 128},
    })
    try:
        parsed = json.loads(event["response"])
    except json.JSONDecodeError:
        parsed = None
    if family == "extraction":
        parsed = _normalize_extraction(parsed)
        required = {key: expected[key] for key in (
            "supplier_name", "invoice_reference", "payment_amount"
        )}
        refs = {key: f"fixture:{key}" for key in CONTROL_IDS}
        execution = execute_supplier_payment_review(
            actor_role="finance_reviewer", evidence_references=refs,
            variable_fields=parsed or {}, human_approved=True,
            cartridge_path=cartridge, signature_path=signature, trust_anchors_path=trust,
        ) if parsed else None
        passed = bool(
            parsed == required and execution and execution.review_complete
            and verify_proof_receipt(execution.proof_receipt)
            and not execution.payment_execution_allowed
        )
    elif family == "drafting":
        passed = isinstance(parsed, dict) and set(parsed) == {"sentence_1", "sentence_2"}
        combined = " ".join(str(parsed.get(key, "")) for key in (
            "sentence_1", "sentence_2"
        )) if passed else ""
        passed = passed and all(
            term.casefold() in combined.casefold() for term in expected["terms"]
        )
    elif family == "planning":
        steps = parsed.get("steps") if isinstance(parsed, dict) else None
        passed = isinstance(steps, list) and len(steps) == 3 and all(
            term.casefold() in str(steps[index]).casefold()
            for index, term in enumerate(expected["ordered_terms"])
        )
    else:
        expression = parsed.get("expression") if isinstance(parsed, dict) else None
        value = _safe_arithmetic(expression) if isinstance(expression, str) else None
        passed = value is not None and str(value) == expected["expected"]
    eval_seconds = int(event.get("eval_duration", 0)) / 1e9
    metrics = {
        "call_number": call_number, "cold_call": call_number == 1,
        "wall_seconds": wall_seconds,
        "load_seconds": int(event.get("load_duration", 0)) / 1e9,
        "prompt_eval_seconds": int(event.get("prompt_eval_duration", 0)) / 1e9,
        "prompt_tokens": int(event.get("prompt_eval_count", 0)),
        "generated_tokens": int(event.get("eval_count", 0)),
        "generation_tokens_per_second": (
            int(event.get("eval_count", 0)) / eval_seconds if eval_seconds else None
        ),
    }
    return passed, metrics, parsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--answers", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--learning-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--seed", type=int, default=170907)
    parser.add_argument("--base-url", default="http://127.0.0.1:11435")
    parser.add_argument("--model", default="qwen3:1.7b")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {
        "tasks": args.tasks.resolve(), "answers": args.answers.resolve(),
        "bundle": args.bundle.resolve(), "learning_root": args.learning_root.resolve(),
    }
    output = args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all manifests, runtime state and evidence must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    task_document = json.loads(paths["tasks"].read_text())
    if task_document.get("schema_version") != "aion.business_holdout_tasks.v1":
        raise RuntimeError("unsupported task manifest")
    tasks = list(task_document["cases"])
    random.Random(args.seed).shuffle(tasks)
    order_hash = _canonical_sha256([
        {"case_id": item["case_id"],
         "request_sha256": hashlib.sha256(item["request"].encode()).hexdigest()}
        for item in tasks
    ])
    cartridge = paths["bundle"] / "supplier_payment_controls.v1.json"
    signature = paths["bundle"] / "supplier_payment_controls.v1.sig.json"
    trust = paths["bundle"] / "trust_anchors.v1.json"
    runtime_root = root / "runtime-evidence" / args.run_id
    trace_path = runtime_root / "trace.jsonl"
    router = GovernedBusinessRouter(
        runtime=AdaptiveInferenceRuntime(
            replay_path=runtime_root / "replay.sqlite3", trace_path=trace_path,
            learned_store=LearnedAtomSheetStore(
                paths["learning_root"] / "learning.sqlite3",
                paths["learning_root"] / "promoted",
            ),
        ), cartridge_path=cartridge, signature_path=signature, trust_anchors_path=trust,
    )

    # Route every request before opening the separate answer key.
    routed = []
    for task in tasks:
        started = time.perf_counter()
        outcome = router.route(task["request"])
        routed.append({
            "task": task, "outcome": outcome,
            "route_seconds": time.perf_counter() - started,
        })
    answer_document = json.loads(paths["answers"].read_text())
    if answer_document.get("schema_version") != "aion.business_holdout_answers.v1":
        raise RuntimeError("unsupported answer manifest")
    answers = answer_document["answers"]
    expected_valid_ids = {
        item["case_id"] for item in tasks if item["expected_disposition"] == "complete"
    }
    if set(answers) != expected_valid_ids:
        raise RuntimeError("answer key does not exactly cover valid task IDs")

    unload, _ = _post(args.base_url, {"model": args.model, "keep_alive": 0})
    results, model_call_number = [], 0
    for item in routed:
        task, outcome = item["task"], item["outcome"]
        valid = task["expected_disposition"] == "complete"
        model_metrics, parsed = None, None
        completed = False
        rejected_verified_bypass = False
        if not valid:
            rejected_verified_bypass = (
                outcome.route not in VERIFIED_ROUTES and not outcome.task_completed
            )
        elif outcome.model_call_required:
            model_call_number += 1
            completed, model_metrics, parsed = _evaluate_model_task(
                task=task, expected=answers[task["case_id"]], model=args.model,
                base_url=args.base_url, call_number=model_call_number,
                cartridge=cartridge, signature=signature, trust=trust,
            )
        elif task["family"] == "calculation":
            completed = outcome.task_completed and outcome.answer == answers[task["case_id"]]["expected"]
        elif task["family"] == "quotation":
            completed = outcome.task_completed and (
                f"total EUR {answers[task['case_id']]['expected_total']}" in (outcome.answer or "")
            )
        elif task["family"] == "policy":
            lines = (outcome.answer or "").splitlines()
            completed = outcome.task_completed and len(lines) == answers[task["case_id"]]["expected_controls"]
            completed = completed and all(
                "Risk prevented:" in line and "human evidence required:" in line for line in lines
            )
        total_seconds = item["route_seconds"] + (
            model_metrics["wall_seconds"] if model_metrics else 0.0
        )
        results.append({
            "case_id": task["case_id"], "family_revealed_after_route": task["family"],
            "expected_disposition_revealed_after_route": task["expected_disposition"],
            "request_sha256": hashlib.sha256(task["request"].encode()).hexdigest(),
            "selected_route": outcome.route,
            "route_receipt_valid": verify_proof_receipt(outcome.proof_receipt),
            "task_completed": completed,
            "rejected_verified_bypass": rejected_verified_bypass,
            "adversarial_model_call_executed": bool(not valid and model_metrics),
            "route_seconds": item["route_seconds"], "elapsed_seconds": total_seconds,
            "model_metrics": model_metrics,
            "response_sha256": _canonical_sha256(parsed) if parsed is not None else None,
        })

    valid_results = [item for item in results if item["expected_disposition_revealed_after_route"] == "complete"]
    adversarial = [item for item in results if item["expected_disposition_revealed_after_route"] != "complete"]
    families = sorted({item["family_revealed_after_route"] for item in results})
    family_summary = {}
    for family in families:
        valid_family = [item for item in valid_results if item["family_revealed_after_route"] == family]
        invalid_family = [item for item in adversarial if item["family_revealed_after_route"] == family]
        durations = [item["elapsed_seconds"] for item in valid_family]
        family_summary[family] = {
            "valid_tasks": len(valid_family),
            "valid_completed": sum(item["task_completed"] for item in valid_family),
            "adversarial_tasks": len(invalid_family),
            "adversarial_verified_bypasses": sum(not item["rejected_verified_bypass"] for item in invalid_family),
            "valid_p50_seconds": statistics.median(durations),
            "valid_p95_seconds_nearest_rank": _p95(durations),
        }
    valid_durations = [item["elapsed_seconds"] for item in valid_results]
    model_calls = [item["model_metrics"] for item in valid_results if item["model_metrics"]]
    warm_calls = [item["wall_seconds"] for item in model_calls[1:]]
    completed_count = sum(item["task_completed"] for item in valid_results)
    adversarial_passes = sum(item["rejected_verified_bypass"] for item in adversarial)
    total_seconds = sum(item["elapsed_seconds"] for item in results)
    acceptance = {
        "frozen_task_and_answer_manifests_hash_bound": True,
        "seven_families_four_valid_and_four_adversarial_each": len(families) == 7 and all(
            item["valid_tasks"] == 4 and item["adversarial_tasks"] == 4
            for item in family_summary.values()
        ),
        "all_28_unseen_valid_tasks_completed": completed_count == 28,
        "all_28_adversarial_near_misses_rejected_verified_bypass": adversarial_passes == 28,
        "zero_adversarial_model_calls_executed": not any(
            item["adversarial_model_call_executed"] for item in adversarial
        ),
        "all_route_receipts_valid": all(item["route_receipt_valid"] for item in results),
        "all_families_passed": all(
            item["valid_completed"] == 4 and item["adversarial_verified_bypasses"] == 0
            for item in family_summary.values()
        ),
        "trace_chain_valid": verify_trace_chain(trace_path),
    }
    report = {
        "schema_version": "aion.business_holdout_result.v1", "run_id": args.run_id,
        "paths": {key: str(value) for key, value in paths.items()},
        "hashes": {"tasks": _sha256(paths["tasks"]), "answers": _sha256(paths["answers"]),
                   "cartridge": _sha256(cartridge), "signature": _sha256(signature),
                   "trust_anchors": _sha256(trust)},
        "method": {"seed": args.seed, "shuffle_order_commitment_sha256": order_hash,
                   "all_requests_routed_before_answer_key_opened": True,
                   "router_received_request_text_only": True,
                   "adversarial_model_execution_prohibited": True,
                   "explicit_qwen_unload_before_valid_model_execution": True,
                   "qwen_unload_done": unload.get("done", False)},
        "results": results, "family_summary": family_summary,
        "aggregate": {"requests": len(results), "valid_tasks": len(valid_results),
                      "valid_completed": completed_count, "adversarial_tasks": len(adversarial),
                      "adversarial_rejected_verified_bypass": adversarial_passes,
                      "serial_wall_seconds_including_route_only_adversarial": total_seconds,
                      "successful_valid_tasks_per_hour": completed_count * 3600 / total_seconds,
                      "valid_task_latency_p50_seconds": statistics.median(valid_durations),
                      "valid_task_latency_p95_seconds_nearest_rank": _p95(valid_durations),
                      "valid_task_latency_max_seconds": max(valid_durations),
                      "model_calls": len(model_calls), "model_calls_avoided_or_prohibited": len(results) - len(model_calls),
                      "qwen_cold_wall_seconds": model_calls[0]["wall_seconds"],
                      "qwen_warm_p50_wall_seconds": statistics.median(warm_calls),
                      "qwen_warm_p95_wall_seconds_nearest_rank": _p95(warm_calls)},
        "acceptance": acceptance, "result": "PASS" if all(acceptance.values()) else "FAIL",
        "claim_boundary": (
            "Frozen synthetic holdout with unseen valid phrasings and adversarial near-misses. "
            "It is not a natural customer distribution, real supplier evidence or a Qwen step-logit test. "
            "Adversarial cases test refusal of verified bypass and are deliberately not executed by a model."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "result": report["result"],
                      "aggregate": report["aggregate"], "family_summary": family_summary,
                      "acceptance": acceptance, "report_sha256": report["report_sha256"]}, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
