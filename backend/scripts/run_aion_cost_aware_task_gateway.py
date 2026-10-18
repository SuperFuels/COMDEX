#!/usr/bin/env python3
"""Measure cost-aware SQI/AtomSheet routing before any model is invoked."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time
from typing import Any

from backend.modules.aion_inference import (
    AdaptiveInferenceRuntime,
    verify_proof_receipt,
    verify_trace_chain,
)


CASES = (
    ("percentage", "What is 15% of 240?", "verified", "36"),
    ("area", "Calculate the area of 5 m by 4 m.", "verified", "20 m²"),
    ("volume", "Calculate volume of 5 m by 4 m by 2.5 m.", "verified", "50 m³"),
    ("conversion", "Convert 2.5 metres to centimetres.", "verified", "250 cm"),
    ("profit", "Revenue is GBP 1000, materials are GBP 200, and labour is GBP 300. Calculate profit.", "verified", "Estimated profit is 500 GBP; profit margin is 50%."),
    ("percentage_replay", "What is 15% of 240?", "replay", "36"),
    ("profit_replay", "Revenue is GBP 1000, materials are GBP 200, and labour is GBP 300. Calculate profit.", "replay", "Estimated profit is 500 GBP; profit margin is 50%."),
    ("conversion_replay", "Convert 2.5 metres to centimetres.", "replay", "250 cm"),
    ("customer_draft", "Write a tactful customer response about a delayed delivery.", "model", None),
    ("business_plan", "Create a five-step plan for introducing a private AI assistant.", "model", None),
    ("coding", "Write a Python function that validates a content hash.", "model", None),
    ("quotation_policy", "Prepare a customer quotation. Do not book or take payment; human review is required.", "model", None),
)


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _p95(values: list[float]) -> float:
    return sorted(values)[max(0, int(0.95 * len(values) + 0.999999) - 1)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    output = (root / "experiments" / f"{args.run_id}.json").resolve()
    runtime_root = (root / "runtime-evidence" / args.run_id).resolve()
    if root not in output.parents or root not in runtime_root.parents:
        raise SystemExit("evidence must remain on external storage")
    if output.exists() or runtime_root.exists():
        raise SystemExit("refusing to overwrite immutable evidence")

    runtime = AdaptiveInferenceRuntime(
        replay_path=runtime_root / "replay.sqlite3",
        trace_path=runtime_root / "trace.jsonl",
    )
    results = []
    for case_id, prompt, expected_class, expected_answer in CASES:
        started = time.perf_counter()
        result = runtime.route(prompt)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        observed_class = (
            "replay" if result.route == "verified_replay"
            else "verified" if result.route == "verified_atomsheet"
            else "model" if result.model_call_required else "unexpected"
        )
        receipt = result.proof_receipt
        answer_correct = expected_answer is None or result.answer == expected_answer
        results.append({
            "case_id": case_id,
            "public_prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "expected_class": expected_class,
            "observed_class": observed_class,
            "route_correct": observed_class == expected_class,
            "answer_correct_or_deferred": answer_correct,
            "route": result.route,
            "model_call_required": result.model_call_required,
            "latency_ms": elapsed_ms,
            "glyph_address": result.glyph_address,
            "proof_receipt_sha256": receipt["proof_receipt_sha256"],
            "proof_receipt_verified": verify_proof_receipt(receipt),
            "collapse_policy": receipt.get("route_collapse_policy"),
            "selected_beam_id": receipt.get("route_collapse", {}).get("selected_beam_id"),
            "beam_count_before_fusion": len(receipt.get("sqi_candidate_beams", ())),
            "execution_count_after_fusion": len(receipt.get("beam_fusion", ())),
        })
    latencies = [item["latency_ms"] for item in results]
    immediate = [item for item in results if not item["model_call_required"]]
    deferred = [item for item in results if item["model_call_required"]]
    integrity = {
        "all_routes_correct": all(item["route_correct"] for item in results),
        "all_verified_answers_correct": all(item["answer_correct_or_deferred"] for item in results),
        "all_proof_receipts_verified": all(item["proof_receipt_verified"] for item in results),
        "trace_chain_verified": verify_trace_chain(runtime_root / "trace.jsonl"),
        "all_collapses_cost_aware": all(
            item["collapse_policy"] == "highest_assurance_then_lowest_estimated_cost"
            for item in results
        ),
    }
    report = {
        "schema_version": "aion.cost_aware_task_gateway.v1",
        "run_id": args.run_id,
        "storage_root": str(root),
        "method": {
            "model_execution_permitted": False,
            "prompt_text_stored": False,
            "task_count": len(results),
            "task_set": "declared deterministic routing fixture, not a population sample",
        },
        "results": results,
        "aggregate": {
            "task_count": len(results),
            "immediately_completed_without_model": len(immediate),
            "correctly_deferred_to_model": len(deferred),
            "model_calls_avoided": len(immediate),
            "model_call_avoidance_percent": 100.0 * len(immediate) / len(results),
            "median_gateway_latency_ms": statistics.median(latencies),
            "p95_gateway_latency_ms_nearest_rank": _p95(latencies),
            "maximum_gateway_latency_ms": max(latencies),
        },
        "integrity": integrity,
        "validation_passed": all(integrity.values()),
        "claim_boundary": (
            "Measures deterministic gateway routing and verified immediate answers only. Model-deferred "
            "tasks are correctly routed but not counted as completed, and no model generation latency "
            "or representative business-workload percentage is claimed."
        ),
    }
    report["report_sha256"] = _hash(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "report_sha256": report["report_sha256"], **report["aggregate"], "integrity": integrity}, indent=2))
    return 0 if report["validation_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
