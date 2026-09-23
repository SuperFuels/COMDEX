#!/usr/bin/env python3
"""Build an evidence-bound mixed-route small-business economics projection."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
from typing import Any


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--atomsheet-evidence", type=Path, required=True)
    parser.add_argument("--qwen-evidence", type=Path, required=True)
    parser.add_argument("--granite-evidence", type=Path, required=True)
    parser.add_argument("--granite-quality", type=Path, required=True)
    parser.add_argument("--business-map-policy-evidence", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    paths = {
        "atomsheet": args.atomsheet_evidence.resolve(),
        "qwen": args.qwen_evidence.resolve(),
        "granite": args.granite_evidence.resolve(),
        "granite_quality": args.granite_quality.resolve(),
    }
    if args.business_map_policy_evidence is not None:
        paths["business_map_policy"] = args.business_map_policy_evidence.resolve()
    output = args.output.resolve()
    if any(root not in path.parents for path in (*paths.values(), output)):
        raise SystemExit("all evidence and output must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite evidence: {output}")
    atomsheet = json.loads(paths["atomsheet"].read_text(encoding="utf-8"))
    qwen = json.loads(paths["qwen"].read_text(encoding="utf-8"))
    granite = json.loads(paths["granite"].read_text(encoding="utf-8"))
    granite_quality = json.loads(paths["granite_quality"].read_text(encoding="utf-8"))
    business_map_policy = (
        json.loads(paths["business_map_policy"].read_text(encoding="utf-8"))
        if "business_map_policy" in paths
        else None
    )

    if atomsheet.get("result") != "PASS" or not all(atomsheet["acceptance"].values()):
        raise RuntimeError("AtomSheet evidence did not pass")
    if qwen.get("result") != "PASS" or not all(qwen["acceptance"].values()):
        raise RuntimeError("Qwen evidence did not pass")
    if not granite["aggregate"]["all_tokens_exact"] or not granite["aggregate"]["all_logits_exact"]:
        raise RuntimeError("Granite exactness evidence did not pass")
    if granite_quality["evidence_file_sha256"] != _sha256(paths["granite"]):
        raise RuntimeError("Granite quality/evidence binding failed")
    if business_map_policy is not None and (
        business_map_policy.get("result") != "PASS"
        or not all(business_map_policy["acceptance"].values())
    ):
        raise RuntimeError("Business Map policy evidence did not pass")

    atomsheet_tasks = int(atomsheet["valid"]["case_count"])
    atomsheet_successes = int(atomsheet["valid"]["pass_count"])
    atomsheet_median_seconds = float(atomsheet["latency"]["median_ms"]) / 1000.0
    atomsheet_p95_seconds = float(atomsheet["latency"]["p95_ms"]) / 1000.0
    atomsheet_projected_seconds = atomsheet_tasks * atomsheet_median_seconds

    # One measured call per distinct Qwen case. The first includes an explicit
    # cold load; the following seven reuse the same installed model.
    qwen_calls = [item["calls"][0] for item in qwen["results"]]
    qwen_seconds = [float(call["wall_seconds"]) for call in qwen_calls]
    qwen_tasks = len(qwen_calls)
    qwen_successes = sum(
        bool(item["extraction_exact_both_repetitions"])
        and bool(item["business_map_review_complete"])
        for item in qwen["results"]
    )

    granite_requests = list(granite["requests"])
    policy_seconds: list[float] = []
    if business_map_policy is not None:
        supplier_requests = [
            item for item in granite_requests if item["family"] == "supplier_payment_controls"
        ]
        if len(supplier_requests) != 1:
            raise RuntimeError("expected exactly one supplier-payment Granite request")
        granite_requests = [
            item for item in granite_requests if item["family"] != "supplier_payment_controls"
        ]
        policy_seconds = [float(business_map_policy["latency"]["median_seconds"])]
    granite_seconds = [float(item["seconds"]) for item in granite_requests]
    granite_tasks = len(granite_seconds)
    quality_by_family = {
        item["family"]: bool(item["task_passed"])
        for item in granite_quality["task_results"]
    }
    granite_successes = sum(
        quality_by_family.get(item["family"], False) for item in granite_requests
    )
    policy_tasks = len(policy_seconds)
    policy_successes = policy_tasks

    total_tasks = atomsheet_tasks + qwen_tasks + policy_tasks + granite_tasks
    total_successes = (
        atomsheet_successes + qwen_successes + policy_successes + granite_successes
    )
    total_seconds = (
        atomsheet_projected_seconds
        + sum(qwen_seconds)
        + sum(policy_seconds)
        + sum(granite_seconds)
    )
    time_by_route = {
        "verified_atomsheet": atomsheet_projected_seconds,
        "qwen_low_cost": sum(qwen_seconds),
        "verified_business_map_policy": sum(policy_seconds),
        "granite_storage_first": sum(granite_seconds),
    }
    report = {
        "schema_version": (
            "aion.small-business-route-economics.v2"
            if business_map_policy is not None
            else "aion.small-business-route-economics.v1"
        ),
        "paths": {key: str(value) for key, value in paths.items()},
        "hashes": {key: _sha256(value) for key, value in paths.items()},
        "scenario": {
            "kind": "evidence_bound_projection_not_blinded_live_run",
            "verified_calculation_tasks": atomsheet_tasks,
            "distinct_qwen_extraction_tasks": qwen_tasks,
            "granite_depth_or_policy_tasks": granite_tasks,
            "verified_business_map_policy_tasks": policy_tasks,
            "qwen_first_task_includes_cold_model_load": True,
            "atomsheet_total_time_uses_measured_median_per_task": True,
            "qwen_and_granite_use_individual_measured_wall_times": True,
            "business_map_policy_uses_measured_median_per_task": business_map_policy is not None,
        },
        "routes": {
            "verified_atomsheet": {
                "tasks": atomsheet_tasks,
                "successful_tasks": atomsheet_successes,
                "median_seconds": atomsheet_median_seconds,
                "p95_seconds": atomsheet_p95_seconds,
                "projected_total_seconds": atomsheet_projected_seconds,
                "model_calls": 0,
            },
            "qwen_low_cost": {
                "tasks": qwen_tasks,
                "successful_tasks": qwen_successes,
                "median_seconds": statistics.median(qwen_seconds),
                "p95_seconds": _p95(qwen_seconds),
                "measured_total_seconds": sum(qwen_seconds),
                "model_calls": qwen_tasks,
                "cold_load_seconds_first_task": float(qwen_calls[0]["load_seconds"]),
                "payment_execution_allowed": False,
            },
            "verified_business_map_policy": {
                "tasks": policy_tasks,
                "successful_tasks": policy_successes,
                "median_seconds": policy_seconds[0] if policy_seconds else None,
                "projected_total_seconds": sum(policy_seconds),
                "model_calls": 0,
                "proof_receipt_valid": business_map_policy is not None,
                "payment_execution_allowed": False,
            },
            "granite_storage_first": {
                "tasks": granite_tasks,
                "successful_tasks": granite_successes,
                "median_seconds": statistics.median(granite_seconds),
                "p95_seconds": _p95(granite_seconds),
                "measured_total_seconds": sum(granite_seconds),
                "model_calls": granite_tasks,
                "tokens_and_step_logits_exact": True,
                "quality_gate_passed": granite_successes == granite_tasks,
            },
        },
        "aggregate": {
            "attempted_tasks": total_tasks,
            "successful_tasks": total_successes,
            "successful_task_rate_percent": 100.0 * total_successes / total_tasks,
            "projected_or_measured_serial_seconds": total_seconds,
            "successful_tasks_per_hour": total_successes * 3600.0 / total_seconds,
            "model_calls": qwen_tasks + granite_tasks,
            "model_calls_avoided": atomsheet_tasks + policy_tasks,
            "model_call_avoidance_percent": 100.0 * (atomsheet_tasks + policy_tasks) / total_tasks,
            "time_share_percent_by_route": {
                key: 100.0 * value / total_seconds for key, value in time_by_route.items()
            },
            "failed_granite_tasks_time_share_percent": (
                100.0 * sum(granite_seconds) / total_seconds
                if granite_tasks and granite_successes == 0 else None
            ),
        },
        "acceptance": {
            "all_atomsheet_tasks_exact": atomsheet_successes == atomsheet_tasks,
            "all_qwen_tasks_exact_and_review_complete": qwen_successes == qwen_tasks,
            "business_map_policy_exact_and_no_authority": (
                business_map_policy is None
                or (
                    policy_successes == policy_tasks
                    and business_map_policy["acceptance"]["receipt_valid"]
                    and business_map_policy["acceptance"]["payment_execution_never_allowed"]
                )
            ),
            "granite_failures_counted_as_failures": granite_successes < granite_tasks,
            "no_failed_task_counted_as_completed": total_successes
            == atomsheet_successes + qwen_successes + policy_successes,
            "source_artifacts_hash_bound": True,
        },
        "result": "DIAGNOSTIC_PASS_NOT_STAGE7_PROMOTION",
        "decision": (
            "The bounded supplier-control task is now answered from its verified signed Business Map "
            "without a model call. The remaining failed Granite integrity task still dominates elapsed "
            "time and requires a verified workflow, stronger task contract, or human review."
        ),
        "claim_boundary": (
            "This combines immutable results from separate synthetic runs; it is not a blinded "
            "live mixed-workload trial. AtomSheet total time is projected from its measured median. "
            "The Business Map policy time is likewise projected from its 1,000-iteration median. "
            "The Qwen cases are labeled synthetic extraction, and Granite quality failures remain failures."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "report_sha256": report["report_sha256"],
        "aggregate": report["aggregate"],
        "routes": report["routes"],
        "acceptance": report["acceptance"],
        "result": report["result"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
