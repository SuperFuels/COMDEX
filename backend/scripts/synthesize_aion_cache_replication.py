#!/usr/bin/env python3
"""Synthesize broad and anomaly replication evidence without hiding variance."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
from typing import Any


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _load_verified(path: Path, schema: str) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != schema:
        raise RuntimeError(f"unexpected schema: {path}")
    claimed = document.get("report_sha256")
    payload = {key: value for key, value in document.items() if key != "report_sha256"}
    if claimed != _canonical_sha256(payload):
        raise RuntimeError(f"canonical report hash failed: {path}")
    if not document.get("integrity") or not all(document["integrity"].values()):
        raise RuntimeError(f"integrity gate failed: {path}")
    return document


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--broad-evidence", type=Path, required=True)
    parser.add_argument("--anomaly-evidence", type=Path, required=True)
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.storage_root.resolve()
    broad_path, anomaly_path = args.broad_evidence.resolve(), args.anomaly_evidence.resolve()
    output = (args.output or root / "experiments" / f"{args.run_id}.json").resolve()
    if any(root not in path.parents for path in (broad_path, anomaly_path, output)):
        raise SystemExit("all evidence must reside on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite synthesis: {output}")

    broad = _load_verified(broad_path, "aion.promoted_cache_plan_replication.v1")
    anomaly = _load_verified(anomaly_path, "aion.promoted_cache_plan_replication.v1")
    paired_changes = [float(pair["promoted_time_change_percent"]) for pair in broad["paired"]]
    anomaly_change = float(anomaly["paired"][0]["promoted_time_change_percent"])
    findings = {
        "broad_case_count": len(broad["paired"]),
        "broad_promoted_wins": sum(change < 0.0 for change in paired_changes),
        "broad_median_paired_time_change_percent": statistics.median(paired_changes),
        "broad_raw_aggregate_median_time_change_percent": broad["outcomes"][
            "promoted_time_change_percent_vs_uniform"
        ],
        "broad_demand_byte_reduction_percent": broad["outcomes"][
            "promoted_demand_byte_reduction_percent_vs_uniform"
        ],
        "anomalous_case_initial_time_change_percent": paired_changes[1],
        "anomalous_case_abba_time_change_percent": anomaly_change,
        "anomalous_case_abba_demand_byte_reduction_percent": anomaly["outcomes"][
            "promoted_demand_byte_reduction_percent_vs_uniform"
        ],
        "all_outputs_exact": (
            broad["integrity"]["all_token_ids_and_step_logits_exact"]
            and anomaly["integrity"]["all_token_ids_and_step_logits_exact"]
        ),
    }
    conclusions = {
        "replicated_lower_demand_bytes": (
            findings["broad_demand_byte_reduction_percent"] > 0
            and findings["anomalous_case_abba_demand_byte_reduction_percent"] > 0
        ),
        "broad_majority_and_median_pairwise_latency_favour_plan": (
            findings["broad_promoted_wins"] >= 3
            and findings["broad_median_paired_time_change_percent"] < 0
        ),
        "anomaly_reverses_under_abba": (
            findings["anomalous_case_initial_time_change_percent"] > 0
            and findings["anomalous_case_abba_time_change_percent"] < 0
        ),
        "population_latency_claim_allowed": False,
        "plan_status": "promising_experimental_reference_latency_not_population_proven",
    }
    integrity = {
        "both_source_reports_canonically_verified": True,
        "all_source_integrity_gates_passed": True,
        "all_outputs_exact": findings["all_outputs_exact"],
        "broad_four_cases_present": findings["broad_case_count"] == 4,
        "anomaly_abba_present": len(anomaly["trials"]) == 4,
        "sources_and_output_on_external_storage": all(
            root in path.parents for path in (broad_path, anomaly_path, output)
        ),
    }
    report = {
        "schema_version": "aion.cache_replication_synthesis.v1",
        "run_id": args.run_id,
        "storage_root": str(root),
        "sources": {
            "broad_path": str(broad_path), "broad_file_sha256": _sha256(broad_path),
            "broad_report_sha256": broad["report_sha256"],
            "anomaly_path": str(anomaly_path), "anomaly_file_sha256": _sha256(anomaly_path),
            "anomaly_report_sha256": anomaly["report_sha256"],
        },
        "findings": findings,
        "conclusions": conclusions,
        "integrity": integrity,
        "claim_boundary": (
            "The synthesis preserves the failed raw aggregate-median latency result alongside the "
            "paired and ABBA results. Five prompt identities are still insufficient for a population "
            "latency claim, and OS cache and thermal state remain uncontrolled."
        ),
    }
    report["report_sha256"] = _canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "file_sha256": _sha256(output),
                      "report_sha256": report["report_sha256"],
                      "findings": findings, "conclusions": conclusions,
                      "integrity": integrity}, indent=2))
    return 0 if all(integrity.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
