#!/usr/bin/env python3
"""Run a shuffled evaluator-blind mixed workload through the governed router."""

from __future__ import annotations

import argparse
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


SCHEMA = {
    "type": "object",
    "properties": {
        "supplier_name": {"type": "string"},
        "invoice_reference": {"type": "string"},
        "payment_amount": {"type": "string"},
    },
    "required": ["supplier_name", "invoice_reference", "payment_amount"],
    "additionalProperties": False,
}
CONTROL_IDS = (
    "independent_supplier_verification",
    "bank_detail_verification",
    "purchase_order_matching",
    "separation_of_duties",
    "payment_limits",
    "audit_record",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)]


def _post(base_url: str, payload: dict[str, Any]) -> tuple[dict[str, Any], float]:
    request = urllib.request.Request(
        base_url.rstrip("/") + "/api/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=300) as response:
        event = json.loads(response.read())
    return event, time.perf_counter() - started


def _normalize_extraction(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    name = normalized.get("supplier_name")
    if isinstance(name, str):
        normalized["supplier_name"] = re.sub(
            r"^(?:vendor|supplier)\s+", "", name, flags=re.I
        )
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--atomsheet-evidence", type=Path, required=True)
    parser.add_argument("--qwen-manifest", type=Path, required=True)
    parser.add_argument("--granite-prompt-manifest", type=Path, required=True)
    parser.add_argument("--granite-evidence", type=Path, required=True)
    parser.add_argument("--granite-quality", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--learning-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--seed", type=int, default=270907)
    parser.add_argument("--base-url", default="http://127.0.0.1:11435")
    parser.add_argument("--model", default="qwen3:1.7b")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.storage_root.resolve()
    paths = {
        "atomsheet_evidence": args.atomsheet_evidence.resolve(),
        "qwen_manifest": args.qwen_manifest.resolve(),
        "granite_prompt_manifest": args.granite_prompt_manifest.resolve(),
        "granite_evidence": args.granite_evidence.resolve(),
        "granite_quality": args.granite_quality.resolve(),
        "bundle": args.bundle.resolve(),
        "learning_root": args.learning_root.resolve(),
    }
    output = args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all inputs, runtime state and output must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")

    atomsheet = json.loads(paths["atomsheet_evidence"].read_text())
    qwen_manifest = json.loads(paths["qwen_manifest"].read_text())
    prompt_manifest = json.loads(paths["granite_prompt_manifest"].read_text())
    granite_quality = json.loads(paths["granite_quality"].read_text())
    if atomsheet.get("result") != "PASS" or not all(atomsheet["acceptance"].values()):
        raise RuntimeError("AtomSheet source cohort is not promoted")
    if granite_quality["evidence_file_sha256"] != _sha256(paths["granite_evidence"]):
        raise RuntimeError("Granite quality sidecar is not bound to its evidence")

    prompts_by_family = {item["family"]: item["prompt"] for item in prompt_manifest["prompts"]}
    failed_families = {
        item["family"] for item in granite_quality["task_results"] if not item["task_passed"]
    }
    integrity_prompt = prompts_by_family["removable_model_integrity"]
    if "removable_model_integrity" not in failed_families:
        raise RuntimeError("integrity task is not a proven failed contract")
    failed_contracts = {
        hashlib.sha256(integrity_prompt.encode()).hexdigest(): _sha256(paths["granite_quality"])
    }

    tasks = []
    for index, item in enumerate(atomsheet["valid"]["results"]):
        tasks.append({
            "case_id": f"calc-{index:03d}", "kind": "calculation",
            "request": item["prompt"], "expected": item["expected"],
        })
    for item in qwen_manifest["cases"]:
        tasks.append({
            "case_id": item["case_id"], "kind": "qwen_extraction",
            "request": item["request"], "expected": item["expected"],
        })
    tasks.extend((
        {"case_id": "policy-001", "kind": "supplier_policy",
         "request": prompts_by_family["supplier_payment_controls"], "expected": None},
        {"case_id": "integrity-001", "kind": "human_review",
         "request": integrity_prompt, "expected": None},
    ))
    random.Random(args.seed).shuffle(tasks)
    order_commitment = _canonical_sha256([
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
            replay_path=runtime_root / "replay.sqlite3",
            trace_path=trace_path,
            learned_store=LearnedAtomSheetStore(
                paths["learning_root"] / "learning.sqlite3",
                paths["learning_root"] / "promoted",
            ),
        ),
        cartridge_path=cartridge,
        signature_path=signature,
        trust_anchors_path=trust,
        failed_model_contracts=failed_contracts,
    )
    unload, _ = _post(args.base_url, {"model": args.model, "keep_alive": 0})
    evidence_refs = {key: f"fixture:{key}" for key in CONTROL_IDS}
    results = []
    qwen_call_number = 0
    for task in tasks:
        started = time.perf_counter()
        routed = router.route(task["request"])
        model_metrics = None
        actual = routed.answer
        completed = routed.task_completed
        if routed.route == "qwen_low_cost":
            qwen_call_number += 1
            event, model_wall = _post(args.base_url, {
                "model": args.model,
                "prompt": (
                    "Extract the three fields exactly as written. Do not infer, calculate, or add text.\n"
                    f"REQUEST: {task['request']}"
                ),
                "stream": False, "think": False, "format": SCHEMA, "keep_alive": "10m",
                "options": {"temperature": 0, "seed": 0, "num_predict": 96},
            })
            try:
                actual = _normalize_extraction(json.loads(event["response"]))
            except json.JSONDecodeError:
                actual = None
            execution = execute_supplier_payment_review(
                actor_role="finance_reviewer", evidence_references=evidence_refs,
                variable_fields=actual or {}, human_approved=True,
                cartridge_path=cartridge, signature_path=signature, trust_anchors_path=trust,
            ) if actual else None
            completed = bool(
                actual == task["expected"] and execution and execution.review_complete
                and verify_proof_receipt(execution.proof_receipt)
                and not execution.payment_execution_allowed
            )
            eval_seconds = int(event.get("eval_duration", 0)) / 1e9
            model_metrics = {
                "call_number": qwen_call_number,
                "cold_call": qwen_call_number == 1,
                "wall_seconds": model_wall,
                "load_seconds": int(event.get("load_duration", 0)) / 1e9,
                "prompt_tokens": int(event.get("prompt_eval_count", 0)),
                "generated_tokens": int(event.get("eval_count", 0)),
                "generation_tokens_per_second": (
                    int(event.get("eval_count", 0)) / eval_seconds if eval_seconds else None
                ),
            }
        elif task["kind"] == "calculation":
            completed = completed and actual == task["expected"]
        elif task["kind"] == "supplier_policy":
            lines = (actual or "").splitlines()
            completed = completed and len(lines) == 6 and all(
                "Risk prevented:" in line and "human evidence required:" in line for line in lines
            )
        elif task["kind"] == "human_review":
            completed = False

        elapsed = time.perf_counter() - started
        results.append({
            "case_id": task["case_id"],
            "request_sha256": hashlib.sha256(task["request"].encode()).hexdigest(),
            "expected_kind_revealed_after_route": task["kind"],
            "selected_route": routed.route,
            "route_receipt_valid": verify_proof_receipt(routed.proof_receipt),
            "human_review_required": routed.human_review_required,
            "task_completed": completed,
            "elapsed_seconds": elapsed,
            "model_metrics": model_metrics,
        })

    elapsed_values = [item["elapsed_seconds"] for item in results]
    qwen_results = [item for item in results if item["model_metrics"]]
    warm_qwen = [item["model_metrics"]["wall_seconds"] for item in qwen_results[1:]]
    completed_count = sum(item["task_completed"] for item in results)
    human_review_count = sum(item["human_review_required"] for item in results)
    total_seconds = sum(elapsed_values)
    route_counts = {
        route: sum(item["selected_route"] == route for item in results)
        for route in sorted({item["selected_route"] for item in results})
    }
    acceptance = {
        "all_route_receipts_valid": all(item["route_receipt_valid"] for item in results),
        "all_109_bounded_tasks_completed": completed_count == 109,
        "exactly_one_task_sent_to_human_review": human_review_count == 1,
        "failed_integrity_contract_not_retried": all(
            item["selected_route"] == "human_review_required"
            for item in results if item["expected_kind_revealed_after_route"] == "human_review"
        ),
        "all_qwen_extractions_completed": all(item["task_completed"] for item in qwen_results),
        "no_granite_calls": "granite_storage_first" not in route_counts,
        "trace_chain_valid": verify_trace_chain(trace_path),
    }
    report = {
        "schema_version": "aion.blinded_small_business_router.v1",
        "run_id": args.run_id,
        "paths": {key: str(value) for key, value in paths.items()},
        "hashes": {key: _sha256(value) for key, value in paths.items() if value.is_file()},
        "installed_business_map_hashes": {
            "cartridge": _sha256(cartridge), "signature": _sha256(signature),
            "trust_anchors": _sha256(trust),
        },
        "method": {
            "seed": args.seed,
            "shuffle_order_commitment_sha256": order_commitment,
            "route_received_request_text_only": True,
            "expected_kind_and_answer_applied_only_by_post_route_evaluator": True,
            "explicit_qwen_unload_before_workload": True,
            "qwen_unload_done": unload.get("done", False),
        },
        "results": results,
        "aggregate": {
            "attempted_tasks": len(results), "completed_tasks": completed_count,
            "completion_rate_percent": 100 * completed_count / len(results),
            "human_review_tasks": human_review_count,
            "safe_resolutions_including_human_review": completed_count + human_review_count,
            "serial_wall_seconds": total_seconds,
            "successful_tasks_per_hour": completed_count * 3600 / total_seconds,
            "task_latency_p50_seconds": statistics.median(elapsed_values),
            "task_latency_p95_seconds_nearest_rank": _p95(elapsed_values),
            "task_latency_max_seconds": max(elapsed_values),
            "model_calls": len(qwen_results), "model_calls_avoided": len(results) - len(qwen_results),
            "route_counts": route_counts,
            "qwen_cold_wall_seconds": qwen_results[0]["model_metrics"]["wall_seconds"],
            "qwen_warm_p50_wall_seconds": statistics.median(warm_qwen),
            "qwen_warm_p95_wall_seconds_nearest_rank": _p95(warm_qwen),
        },
        "acceptance": acceptance,
        "result": "PASS" if all(acceptance.values()) else "FAIL",
        "claim_boundary": (
            "Evaluator-blind shuffled execution of a bounded synthetic 110-task cohort. "
            "It is not a customer workload, Qwen exposes no step logits, fixture evidence is not "
            "real supplier evidence, and the human-review outcome is a safe resolution but not a completed task."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "output": str(output), "result": report["result"],
        "aggregate": report["aggregate"], "acceptance": acceptance,
        "report_sha256": report["report_sha256"],
    }, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
