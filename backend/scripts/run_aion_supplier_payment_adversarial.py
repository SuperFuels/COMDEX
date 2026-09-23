#!/usr/bin/env python3
"""Run fail-closed supplier-payment adversarial fixtures from SD."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time
from typing import Any

from backend.modules.aion_inference import assess_supplier_payment_request, verify_proof_receipt


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--iterations", type=int, default=1000)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    manifest_path = args.manifest.resolve()
    output = root / "experiments" / f"{args.run_id}.json"
    if root not in manifest_path.parents or output.exists():
        raise SystemExit("manifest must be on SD and evidence may not be overwritten")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "aion.supplier_payment_adversarial_manifest.v1":
        raise SystemExit("unsupported adversarial manifest")
    results = []
    latencies = []
    for case in manifest["cases"]:
        decisions = []
        case_latencies = []
        for _ in range(args.iterations):
            started = time.perf_counter_ns()
            decision = assess_supplier_payment_request(
                public_request=case["public_request"], extracted_fields=case["fields"],
                active_tenant_id="tenant:demo-a", requested_tenant_id=case["requested_tenant_id"],
                actor_role="finance_reviewer", known_invoice_references=case["known_invoices"],
                role_limits=case["limits"], evidence_passages=case["evidence"],
            )
            elapsed = (time.perf_counter_ns() - started) / 1e6
            case_latencies.append(elapsed)
            decisions.append(decision)
        latencies.extend(case_latencies)
        expected_reason = case["expected_reason"]
        passed = all(
            item.safe_for_cartridge_execution == case["expected_safe"]
            and (expected_reason is None or expected_reason in item.reasons)
            and not item.model_call_required
            and verify_proof_receipt(item.proof_receipt)
            for item in decisions
        )
        results.append({
            "case_id": case["case_id"], "passed": passed,
            "route": decisions[0].route, "reasons": decisions[0].reasons,
            "distinct_receipts": len({item.proof_receipt["proof_receipt_sha256"] for item in decisions}),
            "median_latency_ms": statistics.median(case_latencies),
        })
    ordered = sorted(latencies)
    report = {
        "schema_version": "aion.supplier_payment_adversarial.v1",
        "run_id": args.run_id,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "case_count": len(results), "iterations_per_case": args.iterations,
        "results": results,
        "summary": {
            "all_cases_passed": all(item["passed"] for item in results),
            "all_receipts_deterministic_per_case": all(item["distinct_receipts"] == 1 for item in results),
            "model_calls": 0,
            "median_latency_ms": statistics.median(latencies),
            "p95_latency_ms_nearest_rank": ordered[max(0, int(.95 * len(ordered) + .999999) - 1)],
        },
        "claim_boundary": "Fixtures use labeled synthetic fields, tenant IDs, invoice history, limits and evidence strings. This proves deterministic routing behavior, not authenticity of real evidence or identities.",
    }
    report["report_sha256"] = _hash(report)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "summary": report["summary"],
                      "report_sha256": report["report_sha256"]}, indent=2))
    return 0 if (
        report["summary"]["all_cases_passed"]
        and report["summary"]["all_receipts_deterministic_per_case"]
        and report["summary"]["model_calls"] == 0
    ) else 2


if __name__ == "__main__":
    raise SystemExit(main())
