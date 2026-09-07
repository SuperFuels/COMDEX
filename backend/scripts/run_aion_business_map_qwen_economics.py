#!/usr/bin/env python3
"""Measure governed Qwen extraction into an SD-resident Business Map."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time
from typing import Any
import urllib.request
import re

from backend.modules.aion_inference import (
    AdaptiveInferenceRuntime,
    execute_supplier_payment_review,
    select_task_model,
    verify_business_map_cartridge,
    verify_proof_receipt,
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
    "independent_supplier_verification", "bank_detail_verification", "purchase_order_matching",
    "separation_of_duties", "payment_limits", "audit_record",
)


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, int(0.95 * len(ordered) + 0.999999) - 1)]


def _normalize_extraction(value: Any) -> tuple[Any, tuple[str, ...]]:
    if not isinstance(value, dict):
        return value, ()
    normalized = dict(value)
    changes: list[str] = []
    supplier_name = normalized.get("supplier_name")
    if isinstance(supplier_name, str):
        canonical = re.sub(r"^(?:vendor|supplier)\s+", "", supplier_name, flags=re.I)
        if canonical != supplier_name:
            normalized["supplier_name"] = canonical
            changes.append("strip_leading_supplier_role_label")
    return normalized, tuple(changes)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:11435")
    parser.add_argument("--model", default="qwen3:1.7b")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.storage_root.resolve()
    manifest_path = args.manifest.resolve()
    bundle = args.bundle.resolve()
    output = (args.output or root / "experiments" / f"{args.run_id}.json").resolve()
    if any(root not in path.parents for path in (manifest_path, bundle, output)):
        raise SystemExit("manifest, installed bundle and evidence must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "aion.supplier_payment_extraction_manifest.v1":
        raise SystemExit("unsupported extraction manifest")

    cartridge = bundle / "supplier_payment_controls.v1.json"
    signature = bundle / "supplier_payment_controls.v1.sig.json"
    trust = bundle / "trust_anchors.v1.json"
    verification = verify_business_map_cartridge(cartridge, signature, trust)
    if not verification.passed:
        raise RuntimeError(f"installed Business Map failed closed: {verification.reasons}")

    unload, _ = _post(args.base_url, {"model": args.model, "keep_alive": 0})
    runtime_root = root / "runtime-evidence" / args.run_id
    runtime = AdaptiveInferenceRuntime(
        replay_path=runtime_root / "replay.sqlite3", trace_path=runtime_root / "trace.jsonl"
    )
    evidence_refs = {control_id: f"fixture:{control_id}" for control_id in CONTROL_IDS}
    results = []
    for case_index, case in enumerate(manifest["cases"]):
        routed = runtime.route(case["request"])
        decision = select_task_model(routed, case["request"])
        prompt = (
            "Extract the three fields exactly as written. Do not infer, calculate, or add text.\n"
            f"REQUEST: {case['request']}"
        )
        calls = []
        for repetition in range(2):
            event, wall_seconds = _post(args.base_url, {
                "model": args.model, "prompt": prompt, "stream": False, "think": False,
                "format": SCHEMA, "keep_alive": "10m",
                "options": {"temperature": 0, "seed": 0, "num_predict": 96},
            })
            try:
                raw_parsed = json.loads(event["response"])
            except json.JSONDecodeError:
                raw_parsed = None
            parsed, normalizations = _normalize_extraction(raw_parsed)
            eval_seconds = int(event.get("eval_duration", 0)) / 1e9
            calls.append({
                "repetition": repetition + 1,
                "wall_seconds": wall_seconds,
                "load_seconds": int(event.get("load_duration", 0)) / 1e9,
                "prompt_tokens": int(event.get("prompt_eval_count", 0)),
                "generated_tokens": int(event.get("eval_count", 0)),
                "generation_seconds": eval_seconds,
                "tokens_per_second": int(event.get("eval_count", 0)) / eval_seconds if eval_seconds else None,
                "done_reason": event.get("done_reason"),
                "response_sha256": hashlib.sha256(event["response"].encode()).hexdigest(),
                "raw_parsed": raw_parsed,
                "parsed": parsed,
                "normalizations": normalizations,
            })
        extraction_exact = all(call["parsed"] == case["expected"] for call in calls)
        deterministic = calls[0]["response_sha256"] == calls[1]["response_sha256"]
        execution = execute_supplier_payment_review(
            actor_role="finance_reviewer",
            evidence_references=evidence_refs,
            variable_fields=calls[0]["parsed"] or {},
            human_approved=True,
            cartridge_path=cartridge,
            signature_path=signature,
            trust_anchors_path=trust,
        ) if calls[0]["parsed"] else None
        results.append({
            "case_id": case["case_id"],
            "request_sha256": hashlib.sha256(case["request"].encode()).hexdigest(),
            "expected": case["expected"],
            "route": decision.to_dict(),
            "calls": calls,
            "extraction_exact_both_repetitions": extraction_exact,
            "response_deterministic": deterministic,
            "business_map_review_complete": bool(execution and execution.review_complete),
            "business_map_receipt_valid": bool(execution and verify_proof_receipt(execution.proof_receipt)),
            "payment_execution_allowed": bool(execution and execution.payment_execution_allowed),
        })

    warm_calls = [call for item in results for call in item["calls"]][1:]
    wall = [float(call["wall_seconds"]) for call in warm_calls]
    tps = [float(call["tokens_per_second"]) for call in warm_calls if call["tokens_per_second"]]
    acceptance = {
        "installed_cartridge_verified": verification.passed,
        "all_routes_selected_qwen": all(item["route"]["route"] == "qwen_low_cost" for item in results),
        "all_extractions_exact_twice": all(item["extraction_exact_both_repetitions"] for item in results),
        "all_responses_deterministic": all(item["response_deterministic"] for item in results),
        "all_business_map_reviews_complete": all(item["business_map_review_complete"] for item in results),
        "all_business_map_receipts_valid": all(item["business_map_receipt_valid"] for item in results),
        "payment_execution_never_allowed": not any(item["payment_execution_allowed"] for item in results),
    }
    report = {
        "schema_version": "aion.business_map_qwen_economics.v1",
        "run_id": args.run_id,
        "paths": {"storage_root": str(root), "manifest": str(manifest_path), "bundle": str(bundle)},
        "hashes": {"manifest": _sha256(manifest_path), "cartridge": _sha256(cartridge),
                   "signature": _sha256(signature), "trust_anchors": _sha256(trust)},
        "model": args.model,
        "method": {"explicit_unload_before_first_call": True, "repetitions_per_case": 2,
                   "cold_call": results[0]["calls"][0], "unload_done": unload.get("done", False)},
        "results": results,
        "warm_summary": {"call_count": len(warm_calls), "median_wall_seconds": statistics.median(wall),
                         "p95_wall_seconds_nearest_rank": _p95(wall),
                         "median_generation_tokens_per_second": statistics.median(tps),
                         "p95_generation_tokens_per_second_nearest_rank": _p95(tps)},
        "acceptance": acceptance,
        "result": "PASS" if all(acceptance.values()) else "FAIL",
        "claim_boundary": "Ollama does not expose the full per-step logits used by the Granite exactness harness. This validates deterministic labeled-field extraction, signed-cartridge execution and task quality, not Qwen logit equivalence or authenticity of synthetic evidence references.",
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "result": report["result"],
                      "warm_summary": report["warm_summary"], "acceptance": acceptance,
                      "report_sha256": report["report_sha256"]}, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
