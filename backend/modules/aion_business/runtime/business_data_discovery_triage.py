from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from typing import Any, Mapping

from backend.modules.aion_business.runtime.business_data_discovery import (
    SCAN_SCHEMA,
    reconcile_scan,
    validate_manifest,
)


TRIAGE_SCHEMA = "tessaris.business-data-triage-queue.v2"
REQUIRED_REVIEW_FIELDS = (
    "data_classification",
    "canonical_authority",
    "storage_boundary",
    "vault_domain_or_exclusion_reason",
    "backup_and_export",
    "retention_and_deletion",
    "migration_decision",
    "verification_evidence",
)


class BusinessDataTriageError(ValueError):
    pass


def _canonical_digest(value: object) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _area(path: str) -> str:
    parts = [part for part in path.split("/") if part]
    return "/".join(parts[:3]) if parts else "unknown"


def _risk(operation: str, path: str) -> tuple[str, str]:
    if operation in {"web.local_storage", "web.indexed_db", "node.sqlite", "python.sqlite.connect"}:
        return "critical", "durable_browser_or_database_state"
    if operation in {
        "web.session_storage", "node.fs.write", "python.file.open_write",
        "python.json.dump", "python.path.write_bytes", "python.path.write_text",
    }:
        return "high", "record_or_file_write"
    if operation == "python.shutil.copy":
        return "high", "file_copy_or_migration"
    if operation in {"node.fs.mkdir", "python.path.mkdir"}:
        return "medium", "directory_creation"
    if operation == "python.tempfile":
        return "medium", "temporary_storage"
    return "high", "unclassified_persistence_operation"


def build_business_data_triage_queue(
    *, scan: Mapping[str, Any], manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Create a deterministic content-free queue for unknown and blocked writes.

    Risk is only ordering metadata. It is never an automatic data classification
    and cannot turn an unknown or declared-blocking write into an approved destination.
    """

    if scan.get("schema_version") != SCAN_SCHEMA:
        raise BusinessDataTriageError("triage_scan_schema_invalid")
    validate_manifest(dict(manifest))
    reconciliation = reconcile_scan(dict(scan), dict(manifest))
    unknown_findings = [
        {**item, "review_status": "unclassified", "touchpoint_id": None}
        for item in reconciliation["unknown_findings"]
    ]
    blocking_ids = set(reconciliation["blocking_touchpoint_ids"])
    blocking_findings = [
        {**item, "review_status": "declared_blocking"}
        for item in reconciliation["declared_findings"]
        if item["touchpoint_id"] in blocking_ids
    ]
    findings = unknown_findings + blocking_findings
    finding_ids = [str(item.get("finding_id") or "") for item in findings]
    if any(not value for value in finding_ids) or len(finding_ids) != len(set(finding_ids)):
        raise BusinessDataTriageError("triage_finding_identity_invalid")

    entries: list[dict[str, Any]] = []
    for finding in sorted(
        findings,
        key=lambda item: (
            str(item.get("path") or ""), int(item.get("line") or 0),
            str(item.get("operation") or ""), str(item.get("finding_id") or ""),
        ),
    ):
        path = str(finding["path"])
        operation = str(finding["operation"])
        risk_level, persistence_kind = _risk(operation, path)
        entries.append(
            {
                "finding_id": str(finding["finding_id"]),
                "path": path,
                "line": int(finding["line"]),
                "language": str(finding["language"]),
                "operation": operation,
                "area": _area(path),
                "risk_level": risk_level,
                "persistence_kind": persistence_kind,
                "review_status": str(finding["review_status"]),
                "touchpoint_id": finding.get("touchpoint_id"),
                "required_review_fields": list(REQUIRED_REVIEW_FIELDS),
            }
        )

    by_area = Counter(entry["area"] for entry in entries)
    by_operation = Counter(entry["operation"] for entry in entries)
    by_risk = Counter(entry["risk_level"] for entry in entries)
    identity = {
        "scan_sha256": _canonical_digest(scan),
        "manifest_sha256": _canonical_digest(manifest),
        "finding_ids_sha256": _canonical_digest(sorted(finding_ids)),
    }
    return {
        "schema_version": TRIAGE_SCHEMA,
        "privacy": "source_locations_only_no_source_text_or_business_values",
        **identity,
        "unknown_finding_count": len(unknown_findings),
        "declared_blocking_finding_count": len(blocking_findings),
        "blocking_touchpoint_count": reconciliation["blocking_touchpoint_count"],
        "queued_finding_count": len(entries),
        "reviewed_count": 0,
        "unreviewed_count": len(entries),
        "release_ready": (
            len(entries) == 0 and reconciliation["blocking_touchpoint_count"] == 0
        ),
        "summary": {
            "by_review_status": dict(sorted(Counter(
                entry["review_status"] for entry in entries
            ).items())),
            "by_risk": dict(sorted(by_risk.items())),
            "by_operation": dict(sorted(by_operation.items())),
            "by_area": dict(sorted(by_area.items())),
        },
        "entries": entries,
    }
