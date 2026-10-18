from __future__ import annotations

from backend.modules.aion_business.runtime.business_data_discovery_triage import (
    REQUIRED_REVIEW_FIELDS,
    TRIAGE_SCHEMA,
    build_business_data_triage_queue,
)


def _manifest():
    return {
        "schema_version": "tessaris.business-data-manifest.v1",
        "required_discovery_sessions": [
            {"id": "files-documents", "name": "Files", "status": "required"}
        ],
        "touchpoints": [
            {
                "id": "declared-vault-write",
                "feature": "Declared Vault write",
                "business_purpose": "Test",
                "business_owner": "Test",
                "source_globs": ["backend/declared.py"],
                "operations": ["python.path.write_text"],
                "classification": "test",
                "canonical_record": "test",
                "physical_storage": "test",
                "external_destinations": [],
                "lifecycle": "test",
                "backup_export": "test",
                "migration_decision": "test",
                "verification": "test",
                "release_gate": "approved",
            }
        ],
    }


def _scan():
    return {
        "schema_version": "tessaris.business-data-scan.v1",
        "privacy": "source_locations_only_no_business_values",
        "repository_root_name": "COMDEX",
        "scanned_files": 3,
        "finding_count": 3,
        "findings": [
            {
                "finding_id": "declared",
                "path": "backend/declared.py",
                "line": 10,
                "language": "python",
                "operation": "python.path.write_text",
            },
            {
                "finding_id": "browser",
                "path": "desktop/mac/src/new-feature.js",
                "line": 20,
                "language": "javascript",
                "operation": "web.local_storage",
            },
            {
                "finding_id": "file",
                "path": "backend/modules/new_feature/store.py",
                "line": 30,
                "language": "python",
                "operation": "python.path.write_bytes",
            },
        ],
    }


def test_triage_queue_contains_every_unknown_once_and_no_declared_write():
    queue = build_business_data_triage_queue(scan=_scan(), manifest=_manifest())
    assert queue["schema_version"] == TRIAGE_SCHEMA
    assert queue["unknown_finding_count"] == 2
    assert queue["declared_blocking_finding_count"] == 0
    assert queue["queued_finding_count"] == 2
    assert queue["unreviewed_count"] == 2
    assert queue["release_ready"] is False
    indexed = {entry["finding_id"]: entry for entry in queue["entries"]}
    assert set(indexed) == {"browser", "file"}
    assert indexed["browser"]["risk_level"] == "critical"
    assert indexed["browser"]["review_status"] == "unclassified"
    assert indexed["file"]["risk_level"] == "high"
    assert indexed["browser"]["required_review_fields"] == list(REQUIRED_REVIEW_FIELDS)


def test_triage_queue_is_deterministic_and_contains_no_source_or_business_values():
    first = build_business_data_triage_queue(scan=_scan(), manifest=_manifest())
    second = build_business_data_triage_queue(scan=_scan(), manifest=_manifest())
    assert first == second
    encoded = str(first)
    assert "customer@example.com" not in encoded
    assert all("source_text" not in entry for entry in first["entries"])
    assert all("business_value" not in entry for entry in first["entries"])


def test_triage_queue_can_prove_zero_unknown_writes():
    scan = _scan()
    scan["findings"] = [scan["findings"][0]]
    scan["finding_count"] = 1
    queue = build_business_data_triage_queue(scan=scan, manifest=_manifest())
    assert queue["unknown_finding_count"] == 0
    assert queue["declared_blocking_finding_count"] == 0
    assert queue["entries"] == []
    assert queue["release_ready"] is True


def test_triage_queue_keeps_each_declared_blocking_finding_visible():
    manifest = _manifest()
    manifest["touchpoints"][0]["release_gate"] = "blocking"
    queue = build_business_data_triage_queue(scan=_scan(), manifest=manifest)
    assert queue["unknown_finding_count"] == 2
    assert queue["declared_blocking_finding_count"] == 1
    assert queue["queued_finding_count"] == 3
    declared = next(
        entry for entry in queue["entries"] if entry["finding_id"] == "declared"
    )
    assert declared["review_status"] == "declared_blocking"
    assert declared["touchpoint_id"] == "declared-vault-write"
    assert queue["release_ready"] is False
