from __future__ import annotations

import json

import pytest

from backend.modules.aion_business.runtime.business_data_discovery import (
    MANIFEST_SCHEMA,
    ManifestError,
    reconcile_scan,
    scan_repository,
    validate_manifest,
)


def manifest(*, status="complete", touchpoints=None):
    return {
        "schema_version": MANIFEST_SCHEMA,
        "required_discovery_sessions": [
            {"id": "customer-crm", "name": "Customer and CRM", "status": status}
        ],
        "touchpoints": touchpoints or [],
    }


def test_scan_records_locations_but_never_source_values(tmp_path):
    backend = tmp_path / "backend"
    desktop = tmp_path / "desktop"
    backend.mkdir()
    desktop.mkdir()
    (backend / "customer.py").write_text(
        "from pathlib import Path\nPath('secret-customer.json').write_text('private value')\n",
        encoding="utf-8",
    )
    (desktop / "state.js").write_text(
        "localStorage.setItem('customer-email', 'person@example.com');\n",
        encoding="utf-8",
    )

    result = scan_repository(tmp_path)

    assert result["finding_count"] == 2
    assert {item["operation"] for item in result["findings"]} == {
        "python.path.write_text",
        "web.local_storage",
    }
    encoded = json.dumps(result)
    assert "private value" not in encoded
    assert "person@example.com" not in encoded


def test_scan_detects_optional_chained_browser_storage_writes(tmp_path):
    desktop = tmp_path / "desktop"
    desktop.mkdir()
    (desktop / "state.js").write_text(
        "window.localStorage?.setItem('business-record', payload);\n"
        "window.sessionStorage?.setItem?.('meeting-context', context);\n",
        encoding="utf-8",
    )

    result = scan_repository(tmp_path)

    assert result["finding_count"] == 2
    assert {item["operation"] for item in result["findings"]} == {
        "web.local_storage",
        "web.session_storage",
    }


def test_scan_excludes_generated_next_bundles_but_keeps_frontend_source(tmp_path):
    generated = tmp_path / "backend" / "static" / "_next" / "static" / "chunks"
    generated.mkdir(parents=True)
    (generated / "compiled.js").write_text(
        "localStorage.setItem('compiled-copy', 'not-authoritative');\n",
        encoding="utf-8",
    )
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "source.ts").write_text(
        "localStorage.setItem('source-key', 'value');\n", encoding="utf-8",
    )
    result = scan_repository(tmp_path)
    assert result["finding_count"] == 1
    assert result["findings"][0]["path"] == "frontend/source.ts"


def test_reconciliation_requires_declaration_and_completed_discovery(tmp_path):
    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / "customer.py").write_text("open('customer.json', 'w')\n", encoding="utf-8")
    scan = scan_repository(tmp_path)
    declared_manifest = manifest(
        touchpoints=[
            {
                "id": "crm-customer-file",
                "feature": "Customer records",
                "business_purpose": "Maintain customer details",
                "business_owner": "Operations",
                "source_globs": ["backend/customer.py"],
                "operations": ["python.file.open_write"],
                "classification": "confidential",
                "canonical_record": "customer",
                "physical_storage": "business-vault",
                "external_destinations": [],
                "lifecycle": "business-defined",
                "backup_export": "included",
                "migration_decision": "move-to-vault",
                "verification": "pending",
                "release_gate": "approved",
            }
        ]
    )

    result = reconcile_scan(scan, declared_manifest)
    assert result["declared_count"] == 1
    assert result["unknown_count"] == 0
    assert result["blocking_touchpoint_count"] == 0
    assert result["vault_boundary_ready"] is True

    incomplete = reconcile_scan(scan, manifest(status="required", touchpoints=declared_manifest["touchpoints"]))
    assert incomplete["vault_boundary_ready"] is False
    assert incomplete["incomplete_discovery_sessions"] == ["customer-crm"]


def test_unknown_write_fails_readiness(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "export.py").write_text("json.dump(payload, handle)\n", encoding="utf-8")
    result = reconcile_scan(scan_repository(tmp_path), manifest())
    assert result["unknown_count"] == 1
    assert result["vault_boundary_ready"] is False


def test_manifest_rejects_incomplete_touchpoint_contract():
    broken = manifest(touchpoints=[{"id": "missing-fields"}])
    with pytest.raises(ManifestError, match="touchpoint_fields_missing"):
        validate_manifest(broken)


def test_declared_but_unapproved_touchpoint_remains_release_blocking(tmp_path):
    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / "customer.py").write_text("open('customer.json', 'w')\n", encoding="utf-8")
    touchpoint = {
        "id": "crm-customer-file",
        "feature": "Customer records",
        "business_purpose": "Maintain customer details",
        "business_owner": "Operations",
        "source_globs": ["backend/customer.py"],
        "operations": ["python.file.open_write"],
        "classification": "confidential",
        "canonical_record": "customer",
        "physical_storage": "application tree pending migration",
        "external_destinations": [],
        "lifecycle": "business-defined",
        "backup_export": "pending",
        "migration_decision": "move-to-vault",
        "verification": "pending",
        "release_gate": "blocking",
    }
    result = reconcile_scan(
        scan_repository(tmp_path), manifest(touchpoints=[touchpoint]),
    )
    assert result["unknown_count"] == 0
    assert result["blocking_touchpoint_count"] == 1
    assert result["declared_release_blocking_count"] == 1
    assert result["vault_boundary_ready"] is False


def test_manifest_rejects_unknown_release_gate_value():
    touchpoint = {
        "id": "bad-gate",
        "feature": "Bad gate",
        "business_purpose": "Test",
        "business_owner": "Test",
        "source_globs": ["backend/bad.py"],
        "operations": ["python.file.open_write"],
        "classification": "test",
        "canonical_record": "test",
        "physical_storage": "test",
        "external_destinations": [],
        "lifecycle": "test",
        "backup_export": "test",
        "migration_decision": "test",
        "verification": "test",
        "release_gate": "ignore",
    }
    with pytest.raises(ManifestError, match="touchpoint_release_gate_invalid:bad-gate"):
        validate_manifest(manifest(touchpoints=[touchpoint]))
