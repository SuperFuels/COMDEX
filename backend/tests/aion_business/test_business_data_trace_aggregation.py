from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.modules.aion_business.runtime.business_data_external_surface_evidence import (
    BusinessDataExternalSurfaceEvidenceRecorder,
)
from backend.modules.aion_business.runtime.business_data_trace_aggregation import (
    BusinessDataTraceAggregationError,
    aggregate_discovery_session_fragments,
)


ROOT = Path(__file__).resolve().parents[3]
EXPECTED_DOMAINS = {
    "identity-access": [
        "business.map", "business.structure", "business.working_state",
        "departments.map", "departments.intelligence",
        "departments.operational_records", "security.records", "security.audit",
    ],
    "lead-booking-intake": [
        "business.map", "business.working_state", "departments.intelligence",
        "departments.map", "departments.operational_records",
        "onboarding.foundation_session", "onboarding.receipts", "sales.audit",
        "sales.records", "security.records", "work_schedule.records",
    ],
}
EXPECTED_EXTERNAL = {
    "identity-access": ["secret_store"],
    "lead-booking-intake": ["provider_api"],
}


def _fragment(trace_root: Path, session_id: str, surface: str, *, unsafe: int = 0) -> None:
    destination = "business_vault" if unsafe == 0 else "application_boundary"
    payload = {
        "schema_version": "tessaris.business-data-runtime-trace.v1",
        "session_id": session_id,
        "scenario": session_id,
        "surface": surface,
        "evidence_kind": (
            "browser_storage_observations"
            if surface == "desktop_renderer"
            else "process_write_observations"
        ),
        "privacy": "source_locations_and_keyed_path_fingerprints_only_no_raw_paths_or_values",
        "observed_vault_domains": (
            EXPECTED_DOMAINS[session_id] if surface == "desktop_backend" else []
        ),
        "vault_domain_operations": [],
        "observed_external_classes": (
            EXPECTED_EXTERNAL[session_id] if surface == "desktop_backend" else []
        ),
        "event_count": 1,
        "scenario_completed": True,
        "dropped_event_count": 0,
        "complete": True,
        "destination_counts": {destination: 1},
        "unsafe_write_count": unsafe,
        "release_gate_passed": unsafe == 0,
        "grouped_source_operations": [{
            "operation": "file.write",
            "destination_class": destination,
            "source_path": "synthetic.py",
            "line": 1,
            "count": 1,
        }],
        "events": [{
            "operation": "file.write",
            "destination_class": destination,
            "destination_hmac_sha256": "a" * 64,
            "source_path": "synthetic.py",
            "line": 1,
        }],
    }
    trace_root.mkdir(parents=True, exist_ok=True)
    (trace_root / f"{session_id}.{surface}.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_aggregate_requires_every_catalogued_surface_and_combines_content_free_evidence(tmp_path):
    session_id = "identity-access"
    for surface in ("desktop_renderer", "desktop_backend", "electron_main"):
        _fragment(tmp_path, session_id, surface)
    report = aggregate_discovery_session_fragments(
        manifest_path=ROOT / "config/business-data-manifest.v1.json",
        catalogue_path=ROOT / "config/business-data-discovery-scenarios.v1.json",
        trace_root=tmp_path,
        session_id=session_id,
    )
    assert report["release_gate_passed"] is True
    assert report["event_count"] == 3
    assert report["missing_surfaces"] == []
    assert set(report["fragment_sha256"]) == {
        "desktop_renderer", "desktop_backend", "electron_main"
    }
    assert report["observed_vault_domains"] == sorted(EXPECTED_DOMAINS[session_id])
    assert report["missing_vault_domains"] == []
    assert report["unexpected_vault_domains"] == []
    assert report["observed_external_classes"] == EXPECTED_EXTERNAL[session_id]
    assert report["missing_external_classes"] == []


def test_aggregate_fails_closed_for_missing_or_unsafe_surface(tmp_path):
    session_id = "identity-access"
    _fragment(tmp_path, session_id, "desktop_backend")
    _fragment(tmp_path, session_id, "electron_main", unsafe=1)
    report = aggregate_discovery_session_fragments(
        manifest_path=ROOT / "config/business-data-manifest.v1.json",
        catalogue_path=ROOT / "config/business-data-discovery-scenarios.v1.json",
        trace_root=tmp_path,
        session_id=session_id,
    )
    assert report["release_gate_passed"] is False
    assert report["missing_surfaces"] == ["desktop_renderer"]
    assert report["unsafe_write_count"] == 1


def test_aggregate_rejects_unexpected_surface_fragment(tmp_path):
    _fragment(tmp_path, "identity-access", "untrusted_process")
    with pytest.raises(BusinessDataTraceAggregationError, match="surface_unexpected"):
        aggregate_discovery_session_fragments(
            manifest_path=ROOT / "config/business-data-manifest.v1.json",
            catalogue_path=ROOT / "config/business-data-discovery-scenarios.v1.json",
            trace_root=tmp_path,
            session_id="identity-access",
        )


def test_aggregate_fails_closed_when_expected_domain_was_not_exercised(tmp_path):
    session_id = "identity-access"
    for surface in ("desktop_renderer", "desktop_backend", "electron_main"):
        _fragment(tmp_path, session_id, surface)
    backend_path = tmp_path / f"{session_id}.desktop_backend.json"
    backend = json.loads(backend_path.read_text(encoding="utf-8"))
    backend["observed_vault_domains"] = ["security.records"]
    backend_path.write_text(json.dumps(backend), encoding="utf-8")
    report = aggregate_discovery_session_fragments(
        manifest_path=ROOT / "config/business-data-manifest.v1.json",
        catalogue_path=ROOT / "config/business-data-discovery-scenarios.v1.json",
        trace_root=tmp_path,
        session_id=session_id,
    )
    assert report["release_gate_passed"] is False
    assert report["missing_vault_domains"] == [
        "business.map", "business.structure", "business.working_state",
        "departments.intelligence", "departments.map",
        "departments.operational_records", "security.audit",
    ]


def test_aggregate_fails_closed_when_expected_external_class_was_not_exercised(tmp_path):
    session_id = "identity-access"
    for surface in ("desktop_renderer", "desktop_backend", "electron_main"):
        _fragment(tmp_path, session_id, surface)
    backend_path = tmp_path / f"{session_id}.desktop_backend.json"
    backend = json.loads(backend_path.read_text(encoding="utf-8"))
    backend["observed_external_classes"] = []
    backend_path.write_text(json.dumps(backend), encoding="utf-8")
    report = aggregate_discovery_session_fragments(
        manifest_path=ROOT / "config/business-data-manifest.v1.json",
        catalogue_path=ROOT / "config/business-data-discovery-scenarios.v1.json",
        trace_root=tmp_path,
        session_id=session_id,
    )
    assert report["release_gate_passed"] is False
    assert report["missing_external_classes"] == ["secret_store"]


def test_aggregate_requires_complete_declared_provider_class_evidence(tmp_path):
    session_id = "lead-booking-intake"
    _fragment(tmp_path, session_id, "desktop_renderer")
    _fragment(tmp_path, session_id, "desktop_backend")
    recorder = BusinessDataExternalSurfaceEvidenceRecorder(
        manifest_path=ROOT / "config/business-data-manifest.v1.json",
        scenario_catalogue_path=ROOT / "config/business-data-discovery-scenarios.v1.json",
        session_id=session_id,
        scenario=session_id,
        surface="provider_sandbox",
        fingerprint_key=b"aggregate-provider-fingerprint-key!!",
    )
    recorder.record(
        operation="provider.lead.received",
        external_class="provider_api",
        identifier="provider-event-opaque-id",
        approved=True,
    )
    recorder.write_report(
        tmp_path / f"{session_id}.provider_sandbox.json",
        scenario_completed=True,
    )
    report = aggregate_discovery_session_fragments(
        manifest_path=ROOT / "config/business-data-manifest.v1.json",
        catalogue_path=ROOT / "config/business-data-discovery-scenarios.v1.json",
        trace_root=tmp_path,
        session_id=session_id,
    )
    assert report["release_gate_passed"] is True
    assert set(report["included_surfaces"]) == {
        "desktop_renderer", "desktop_backend", "provider_sandbox"
    }
