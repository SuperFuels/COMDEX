#!/usr/bin/env python3
"""Run an evaluator-blind, family-balanced small-business routing cohort."""

from __future__ import annotations

import argparse
import ast
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import random
import re
import statistics
import time
from typing import Any
import urllib.request

from backend.modules.aion_inference import (
    AdaptiveInferenceRuntime,
    GovernedBusinessRouter,
    LearnedAtomSheetStore,
    execute_supplier_payment_review,
    verify_proof_receipt,
    verify_trace_chain,
)


CONTROL_IDS = (
    "independent_supplier_verification", "bank_detail_verification",
    "purchase_order_matching", "separation_of_duties", "payment_limits", "audit_record",
)
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "supplier_name": {"type": "string"}, "invoice_reference": {"type": "string"},
        "payment_amount": {"type": "string"},
    },
    "required": ["supplier_name", "invoice_reference", "payment_amount"],
    "additionalProperties": False,
}
DRAFT_SCHEMA = {
    "type": "object",
    "properties": {"sentence_1": {"type": "string"}, "sentence_2": {"type": "string"}},
    "required": ["sentence_1", "sentence_2"], "additionalProperties": False,
}
PLAN_SCHEMA = {
    "type": "object",
    "properties": {"steps": {"type": "array", "items": {"type": "string"},
                              "minItems": 3, "maxItems": 3}},
    "required": ["steps"], "additionalProperties": False,
}
CODE_SCHEMA = {
    "type": "object", "properties": {"expression": {"type": "string"}},
    "required": ["expression"], "additionalProperties": False,
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()).hexdigest()


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)]


def _post(base_url: str, payload: dict[str, Any]) -> tuple[dict[str, Any], float]:
    request = urllib.request.Request(
        base_url.rstrip("/") + "/api/generate", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=300) as response:
        event = json.loads(response.read())
    return event, time.perf_counter() - started


def _normalize_extraction(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    if isinstance(normalized.get("supplier_name"), str):
        normalized["supplier_name"] = re.sub(
            r"^(?:vendor|supplier)\s+", "", normalized["supplier_name"], flags=re.I
        )
    return normalized


def _safe_arithmetic(expression: str) -> Decimal | None:
    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, ValueError):
        return None

    def visit(node: ast.AST) -> Decimal:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            return Decimal(str(node.value))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and isinstance(
            node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod)
        ):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add): return left + right
            if isinstance(node.op, ast.Sub): return left - right
            if isinstance(node.op, ast.Mult): return left * right
            if isinstance(node.op, ast.Div): return left / right
            if isinstance(node.op, ast.FloorDiv): return left // right
            return left % right
        raise ValueError("unsafe expression")

    try:
        return visit(tree)
    except (ValueError, ArithmeticError):
        return None


def _build_tasks(atomsheet: dict[str, Any], extraction: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = []
    for index, item in enumerate(atomsheet["valid"]["results"][:8]):
        tasks.append({"case_id": f"calc-{index + 1:02d}", "family": "calculation",
                      "request": item["prompt"], "expected": item["expected"]})
    quotation_jobs = (
        ("Patio Repair", "120", "20"), ("Office Painting", "850", "15"),
        ("Window Cleaning", "240.50", "10"), ("Boiler Service", "95", "12.5"),
        ("Garden Clearance", "430", "18"), ("Website Refresh", "1500", "22"),
        ("Roof Inspection", "275", "8"), ("Floor Installation", "3200", "17.5"),
    )
    for index, (job, base, markup) in enumerate(quotation_jobs):
        total = (Decimal(base) * (1 + Decimal(markup) / 100)).quantize(Decimal("0.01"))
        tasks.append({
            "case_id": f"quote-{index + 1:02d}", "family": "quotation",
            "request": f"Prepare a draft quotation for {job}: base EUR {base}, markup {markup}%. "
                       "Do not send it; human approval is required.",
            "expected": f"{total:.2f}",
        })
    policy_requests = (
        "Produce six supplier payment controls. Each must state the risk and human evidence.",
        "List six controls for supplier payments, naming the risk and the human evidence for each.",
        "Explain six supplier payment controls with the risk prevented and human evidence required.",
        "Show six supplier-payment controls; include risk and evidence from a human for every control.",
        "What six controls govern supplier payment risk and the human evidence needed?",
        "Describe six controls before paying a supplier, with risk and human evidence in each.",
        "Give six supplier controls for payment, stating risk plus required human evidence.",
        "Provide six supplier payment safeguards as controls, including risk and human evidence.",
    )
    tasks.extend({"case_id": f"policy-{i + 1:02d}", "family": "policy",
                  "request": request, "expected": None}
                 for i, request in enumerate(policy_requests))
    tasks.extend({"case_id": item["case_id"], "family": "extraction",
                  "request": item["request"], "expected": item["expected"]}
                 for item in extraction["cases"])
    draft_cases = (
        ("Ava", "order", "ready", "Monday"), ("Ben", "repair", "scheduled", "Tuesday"),
        ("Chloe", "quotation", "prepared", "Wednesday"), ("Diego", "delivery", "dispatched", "Thursday"),
        ("Ella", "installation", "confirmed", "Friday"), ("Farah", "refund", "reviewed", "Monday"),
        ("George", "inspection", "completed", "Tuesday"), ("Hana", "booking", "received", "Wednesday"),
    )
    for i, (name, subject, status, update) in enumerate(draft_cases):
        tasks.append({
            "case_id": f"draft-{i + 1:02d}", "family": "drafting",
            "request": f"Write exactly two customer-update sentences. Sentence 1 must address "
                       f"{name} by name and use the exact words: the {subject} is {status}. "
                       f"Sentence 2 must use the exact words: the next update is {update}.",
            "expected": {"terms": [name, subject, status, update]},
        })
    plan_cases = (
        ("stocktake", ("count", "reconcile", "approve")),
        ("supplier onboarding", ("verify", "record", "review")),
        ("invoice review", ("match", "check", "approve")),
        ("customer follow-up", ("review", "draft", "schedule")),
        ("equipment inspection", ("inspect", "record", "escalate")),
        ("weekly cash review", ("collect", "compare", "report")),
        ("job handover", ("confirm", "document", "notify")),
        ("data backup", ("copy", "verify", "record")),
    )
    for i, (topic, words) in enumerate(plan_cases):
        tasks.append({
            "case_id": f"plan-{i + 1:02d}", "family": "planning",
            "request": f"Create exactly three short steps for {topic}. Use these actions in order: "
                       f"{words[0]}, {words[1]}, {words[2]}.",
            "expected": {"ordered_terms": list(words)},
        })
    code_cases = ((17, 6, "*"), (84, 7, "/"), (32, 19, "+"), (95, 28, "-"),
                  (13, 9, "*"), (144, 12, "/"), (71, 22, "+"), (200, 37, "-"))
    for i, (left, right, operator) in enumerate(code_cases):
        expected = _safe_arithmetic(f"{left} {operator} {right}")
        tasks.append({
            "case_id": f"code-{i + 1:02d}", "family": "coding",
            "request": f"Give one Python expression for {left} {operator} {right}, using numeric "
                       "literals and arithmetic operators.",
            "expected": str(expected),
        })
    return tasks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--atomsheet-evidence", type=Path, required=True)
    parser.add_argument("--extraction-manifest", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--learning-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--seed", type=int, default=70907)
    parser.add_argument("--base-url", default="http://127.0.0.1:11435")
    parser.add_argument("--model", default="qwen3:1.7b")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {"atomsheet_evidence": args.atomsheet_evidence.resolve(),
             "extraction_manifest": args.extraction_manifest.resolve(),
             "bundle": args.bundle.resolve(), "learning_root": args.learning_root.resolve()}
    output = args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all inputs, runtime state and evidence must remain on external storage")
    if output.exists(): raise SystemExit(f"refusing to overwrite evidence: {output}")
    atomsheet = json.loads(paths["atomsheet_evidence"].read_text())
    extraction = json.loads(paths["extraction_manifest"].read_text())
    if atomsheet.get("result") != "PASS" or not all(atomsheet["acceptance"].values()):
        raise RuntimeError("AtomSheet source cohort is not promoted")
    tasks = _build_tasks(atomsheet, extraction)
    random.Random(args.seed).shuffle(tasks)
    order_hash = _canonical_sha256([
        {"case_id": item["case_id"], "request_sha256": hashlib.sha256(item["request"].encode()).hexdigest()}
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
            learned_store=LearnedAtomSheetStore(paths["learning_root"] / "learning.sqlite3",
                                                paths["learning_root"] / "promoted"),
        ), cartridge_path=cartridge, signature_path=signature, trust_anchors_path=trust,
    )
    unload, _ = _post(args.base_url, {"model": args.model, "keep_alive": 0})
    evidence_refs = {key: f"fixture:{key}" for key in CONTROL_IDS}
    results, model_call_number = [], 0
    for task in tasks:
        started = time.perf_counter()
        routed = router.route(task["request"])
        completed, parsed, metrics = routed.task_completed, None, None
        if routed.model_call_required:
            model_call_number += 1
            if task["family"] == "extraction":
                schema = EXTRACTION_SCHEMA
                prompt = (
                    "Extract the three fields exactly as written. Do not infer, calculate, or add text.\n"
                    f"REQUEST: {task['request']}"
                )
            elif task["family"] == "drafting":
                schema, prompt = DRAFT_SCHEMA, "Return JSON only. " + task["request"]
            elif task["family"] == "planning":
                schema, prompt = PLAN_SCHEMA, "Return JSON only. " + task["request"]
            elif task["family"] == "coding":
                schema, prompt = CODE_SCHEMA, "Return JSON only. " + task["request"]
            else:
                schema, prompt = {"type": "object"}, task["request"]
            event, model_wall = _post(args.base_url, {
                "model": args.model, "prompt": prompt, "stream": False, "think": False,
                "format": schema, "keep_alive": "10m",
                "options": {"temperature": 0, "seed": 0, "num_predict": 128},
            })
            try: parsed = json.loads(event["response"])
            except json.JSONDecodeError: parsed = None
            if task["family"] == "extraction":
                parsed = _normalize_extraction(parsed)
                execution = execute_supplier_payment_review(
                    actor_role="finance_reviewer", evidence_references=evidence_refs,
                    variable_fields=parsed or {}, human_approved=True, cartridge_path=cartridge,
                    signature_path=signature, trust_anchors_path=trust,
                ) if parsed else None
                completed = bool(parsed == task["expected"] and execution and execution.review_complete
                                 and verify_proof_receipt(execution.proof_receipt)
                                 and not execution.payment_execution_allowed)
            elif task["family"] == "drafting":
                completed = isinstance(parsed, dict) and set(parsed) == {"sentence_1", "sentence_2"}
                combined = " ".join(str(parsed.get(key, "")) for key in ("sentence_1", "sentence_2")) if completed else ""
                completed = completed and all(term.casefold() in combined.casefold()
                                              for term in task["expected"]["terms"])
            elif task["family"] == "planning":
                steps = parsed.get("steps") if isinstance(parsed, dict) else None
                completed = isinstance(steps, list) and len(steps) == 3 and all(
                    term.casefold() in str(steps[index]).casefold()
                    for index, term in enumerate(task["expected"]["ordered_terms"])
                )
            elif task["family"] == "coding":
                expression = parsed.get("expression") if isinstance(parsed, dict) else None
                value = _safe_arithmetic(expression) if isinstance(expression, str) else None
                completed = value is not None and str(value) == task["expected"]
            eval_seconds = int(event.get("eval_duration", 0)) / 1e9
            metrics = {"call_number": model_call_number, "cold_call": model_call_number == 1,
                       "wall_seconds": model_wall,
                       "load_seconds": int(event.get("load_duration", 0)) / 1e9,
                       "prompt_tokens": int(event.get("prompt_eval_count", 0)),
                       "generated_tokens": int(event.get("eval_count", 0)),
                       "generation_tokens_per_second": int(event.get("eval_count", 0)) / eval_seconds
                       if eval_seconds else None}
        elif task["family"] == "calculation":
            completed = completed and routed.answer == task["expected"]
        elif task["family"] == "quotation":
            completed = completed and f"total EUR {task['expected']}" in (routed.answer or "")
        elif task["family"] == "policy":
            lines = (routed.answer or "").splitlines()
            completed = completed and len(lines) == 6 and all(
                "Risk prevented:" in line and "human evidence required:" in line for line in lines
            )
        elif task["family"] == "extraction":
            try:
                parsed = json.loads(routed.answer or "")
            except json.JSONDecodeError:
                parsed = None
            execution = execute_supplier_payment_review(
                actor_role="finance_reviewer", evidence_references=evidence_refs,
                variable_fields=parsed or {}, human_approved=True, cartridge_path=cartridge,
                signature_path=signature, trust_anchors_path=trust,
            ) if parsed else None
            completed = bool(
                completed and parsed == task["expected"] and execution
                and execution.review_complete
                and verify_proof_receipt(execution.proof_receipt)
                and not execution.payment_execution_allowed
            )
        results.append({"case_id": task["case_id"], "family_revealed_after_route": task["family"],
                        "request_sha256": hashlib.sha256(task["request"].encode()).hexdigest(),
                        "selected_route": routed.route, "task_completed": completed,
                        "route_receipt_valid": verify_proof_receipt(routed.proof_receipt),
                        "human_approval_required": routed.human_review_required,
                        "elapsed_seconds": time.perf_counter() - started, "model_metrics": metrics,
                        "response_sha256": _canonical_sha256(parsed) if parsed is not None else None})
    families = sorted({item["family_revealed_after_route"] for item in results})
    family_summary = {}
    for family in families:
        cohort = [item for item in results if item["family_revealed_after_route"] == family]
        durations = [item["elapsed_seconds"] for item in cohort]
        family_summary[family] = {"tasks": len(cohort),
                                  "completed": sum(item["task_completed"] for item in cohort),
                                  "p50_seconds": statistics.median(durations),
                                  "p95_seconds_nearest_rank": _p95(durations),
                                  "model_calls": sum(item["model_metrics"] is not None for item in cohort)}
    durations = [item["elapsed_seconds"] for item in results]
    model_calls = [item["model_metrics"] for item in results if item["model_metrics"]]
    warm_calls = [item["wall_seconds"] for item in model_calls[1:]]
    completed = sum(item["task_completed"] for item in results)
    acceptance = {"seven_families_eight_tasks_each": len(families) == 7 and
                  all(value["tasks"] == 8 for value in family_summary.values()),
                  "all_56_tasks_completed": completed == 56,
                  "all_route_receipts_valid": all(item["route_receipt_valid"] for item in results),
                  "all_families_passed": all(value["completed"] == 8 for value in family_summary.values()),
                  "no_granite_calls": not any(item["selected_route"] == "granite_storage_first" for item in results),
                  "trace_chain_valid": verify_trace_chain(trace_path)}
    total_seconds = sum(durations)
    report = {"schema_version": "aion.balanced_business_router.v1", "run_id": args.run_id,
              "paths": {key: str(value) for key, value in paths.items()},
              "hashes": {key: _sha256(value) for key, value in paths.items() if value.is_file()},
              "business_map_hashes": {"cartridge": _sha256(cartridge), "signature": _sha256(signature),
                                      "trust_anchors": _sha256(trust)},
              "method": {"seed": args.seed, "shuffle_order_commitment_sha256": order_hash,
                         "route_received_request_text_only": True,
                         "expected_family_and_answer_applied_after_route": True,
                         "explicit_qwen_unload_before_workload": True,
                         "qwen_unload_done": unload.get("done", False)},
              "results": results, "family_summary": family_summary,
              "aggregate": {"attempted_tasks": len(results), "completed_tasks": completed,
                            "completion_rate_percent": 100 * completed / len(results),
                            "serial_wall_seconds": total_seconds,
                            "successful_tasks_per_hour": completed * 3600 / total_seconds,
                            "task_latency_p50_seconds": statistics.median(durations),
                            "task_latency_p95_seconds_nearest_rank": _p95(durations),
                            "task_latency_max_seconds": max(durations), "model_calls": len(model_calls),
                            "model_calls_avoided": len(results) - len(model_calls),
                            "qwen_cold_wall_seconds": model_calls[0]["wall_seconds"],
                            "qwen_warm_p50_wall_seconds": statistics.median(warm_calls),
                            "qwen_warm_p95_wall_seconds_nearest_rank": _p95(warm_calls)},
              "acceptance": acceptance, "result": "PASS" if all(acceptance.values()) else "FAIL",
              "claim_boundary": "Evaluator-blind balanced synthetic tasks with deterministic rubrics. Not a real customer workload; Qwen step logits and real supplier evidence authenticity are not available."}
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "result": report["result"],
                      "aggregate": report["aggregate"], "family_summary": family_summary,
                      "acceptance": acceptance, "report_sha256": report["report_sha256"]}, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
