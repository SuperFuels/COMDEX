from __future__ import annotations

import json

import pytest

from backend.modules.aion_business.runtime.business_data_release_evidence import (
    BusinessDataReleaseEvidenceError,
    build_business_data_release_evidence,
)


def _write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def _catalogue(path, sessions):
    _write(path, {
        "schema_version": "tessaris.business-data-discovery-scenarios.v1",
        "privacy": "synthetic-test-catalogue",
        "scenarios": [{
            "session_id": session,
            "execution_surfaces": ["desktop_backend"],
            "journey_steps": ["execute synthetic journey"],
            "expected_domains": ["business.identity"],
            "expected_external_classes": ["none"],
            "completion_assertions": ["synthetic journey completed"],
        } for session in sessions],
    })
    return path


def test_release_evidence_requires_every_passing_trace(tmp_path):
    manifest = tmp_path / "manifest.json"
    _write(manifest, {
        "schema_version": "tessaris.business-data-manifest.v1",
        "required_discovery_sessions": [
            {"id": "onboarding", "name": "Onboarding", "status": "complete"},
            {"id": "departments", "name": "Departments", "status": "complete"},
        ],
        "touchpoints": [],
    })
    audit = tmp_path / "audit.json"
    _write(audit, {"reconciliation": {
        "unknown_count": 0,
        "blocking_touchpoint_count": 0,
        "incomplete_discovery_session_count": 0,
        "vault_boundary_ready": True,
    }})
    traces = []
    catalogue = _catalogue(tmp_path / "scenarios.json", ("onboarding", "departments"))
    for session in ("onboarding", "departments"):
        path = tmp_path / f"{session}.json"
        _write(path, {
            "schema_version": "tessaris.business-data-runtime-trace.v1",
            "session_id": session,
            "scenario": session,
            "surface": "aggregated",
            "required_surfaces": ["desktop_backend"],
            "included_surfaces": ["desktop_backend"],
            "missing_surfaces": [],
            "fragment_sha256": {"desktop_backend": "a" * 64},
            "expected_vault_domains": ["business.identity"],
            "observed_vault_domains": ["business.identity"],
            "missing_vault_domains": [],
            "unexpected_vault_domains": [],
            "expected_external_classes": [],
            "observed_external_classes": [],
            "missing_external_classes": [],
            "unexpected_external_classes": [],
            "event_count": 1,
            "scenario_completed": True,
            "complete": True,
            "release_gate_passed": True,
            "dropped_event_count": 0,
            "unsafe_write_count": 0,
        })
        traces.append(path)
    evidence = build_business_data_release_evidence(
        manifest_path=manifest,
        scenario_catalogue_path=catalogue,
        audit_report_path=audit,
        trace_report_paths=traces,
    )
    assert evidence["runtime_trace_session_count"] == 2
    assert evidence["required_discovery_session_count"] == 2
    assert set(evidence["runtime_trace_sha256"]) == {"onboarding", "departments"}
    assert evidence["runtime_trace_surface_counts"] == {
        "departments": 1,
        "onboarding": 1,
    }
    assert evidence["runtime_trace_domain_counts"] == {
        "departments": 1,
        "onboarding": 1,
    }
    assert evidence["runtime_trace_external_class_counts"] == {
        "departments": 0,
        "onboarding": 0,
    }

    with pytest.raises(BusinessDataReleaseEvidenceError, match="sessions_missing:departments"):
        build_business_data_release_evidence(
            manifest_path=manifest,
            scenario_catalogue_path=catalogue,
            audit_report_path=audit,
            trace_report_paths=traces[:1],
        )


def test_release_evidence_rejects_unknown_write(tmp_path):
    manifest = tmp_path / "manifest.json"
    _write(manifest, {
        "schema_version": "tessaris.business-data-manifest.v1",
        "required_discovery_sessions": [{"id": "one", "name": "One", "status": "complete"}],
        "touchpoints": [],
    })
    audit = tmp_path / "audit.json"
    _write(audit, {"reconciliation": {
        "unknown_count": 1,
        "blocking_touchpoint_count": 0,
        "incomplete_discovery_session_count": 0,
        "vault_boundary_ready": False,
    }})
    with pytest.raises(BusinessDataReleaseEvidenceError, match="unknown_business_data_writes"):
        build_business_data_release_evidence(
            manifest_path=manifest,
            scenario_catalogue_path=_catalogue(tmp_path / "scenarios.json", ("one",)),
            audit_report_path=audit,
            trace_report_paths=[],
        )


def test_release_evidence_rejects_trace_with_forged_or_incomplete_surface_set(tmp_path):
    manifest = tmp_path / "manifest.json"
    _write(manifest, {
        "schema_version": "tessaris.business-data-manifest.v1",
        "required_discovery_sessions": [
            {"id": "identity-access", "name": "Identity", "status": "complete"}
        ],
        "touchpoints": [],
    })
    catalogue = _catalogue(tmp_path / "scenarios.json", ("identity-access",))
    audit = tmp_path / "audit.json"
    _write(audit, {"reconciliation": {
        "unknown_count": 0,
        "blocking_touchpoint_count": 0,
        "incomplete_discovery_session_count": 0,
        "vault_boundary_ready": True,
    }})
    trace = tmp_path / "identity-access.json"
    _write(trace, {
        "schema_version": "tessaris.business-data-runtime-trace.v1",
        "session_id": "identity-access",
        "scenario": "identity-access",
        "surface": "aggregated",
        "required_surfaces": ["desktop_backend"],
        "included_surfaces": [],
        "missing_surfaces": [],
        "fragment_sha256": {},
        "expected_vault_domains": ["business.identity"],
        "observed_vault_domains": ["business.identity"],
        "missing_vault_domains": [],
        "unexpected_vault_domains": [],
        "expected_external_classes": [],
        "observed_external_classes": [],
        "missing_external_classes": [],
        "unexpected_external_classes": [],
        "event_count": 1,
        "scenario_completed": True,
        "complete": True,
        "release_gate_passed": True,
        "dropped_event_count": 0,
        "unsafe_write_count": 0,
    })
    with pytest.raises(BusinessDataReleaseEvidenceError, match="surface_coverage_invalid"):
        build_business_data_release_evidence(
            manifest_path=manifest,
            scenario_catalogue_path=catalogue,
            audit_report_path=audit,
            trace_report_paths=[trace],
        )


def test_release_evidence_rejects_missing_expected_domain(tmp_path):
    manifest = tmp_path / "manifest.json"
    _write(manifest, {
        "schema_version": "tessaris.business-data-manifest.v1",
        "required_discovery_sessions": [
            {"id": "onboarding", "name": "Onboarding", "status": "complete"}
        ],
        "touchpoints": [],
    })
    catalogue = _catalogue(tmp_path / "scenarios.json", ("onboarding",))
    audit = tmp_path / "audit.json"
    _write(audit, {"reconciliation": {
        "unknown_count": 0,
        "blocking_touchpoint_count": 0,
        "incomplete_discovery_session_count": 0,
        "vault_boundary_ready": True,
    }})
    trace = tmp_path / "onboarding.json"
    _write(trace, {
        "schema_version": "tessaris.business-data-runtime-trace.v1",
        "session_id": "onboarding",
        "scenario": "onboarding",
        "surface": "aggregated",
        "required_surfaces": ["desktop_backend"],
        "included_surfaces": ["desktop_backend"],
        "missing_surfaces": [],
        "fragment_sha256": {"desktop_backend": "a" * 64},
        "expected_vault_domains": ["business.identity"],
        "observed_vault_domains": [],
        "missing_vault_domains": ["business.identity"],
        "unexpected_vault_domains": [],
        "expected_external_classes": [],
        "observed_external_classes": [],
        "missing_external_classes": [],
        "unexpected_external_classes": [],
        "event_count": 1,
        "scenario_completed": True,
        "complete": True,
        "release_gate_passed": True,
        "dropped_event_count": 0,
        "unsafe_write_count": 0,
    })
    with pytest.raises(BusinessDataReleaseEvidenceError, match="domain_coverage_invalid"):
        build_business_data_release_evidence(
            manifest_path=manifest,
            scenario_catalogue_path=catalogue,
            audit_report_path=audit,
            trace_report_paths=[trace],
        )


def test_release_evidence_rejects_missing_expected_external_class(tmp_path):
    manifest = tmp_path / "manifest.json"
    _write(manifest, {
        "schema_version": "tessaris.business-data-manifest.v1",
        "required_discovery_sessions": [
            {"id": "onboarding", "name": "Onboarding", "status": "complete"}
        ],
        "touchpoints": [],
    })
    catalogue = tmp_path / "scenarios.json"
    _write(catalogue, {
        "schema_version": "tessaris.business-data-discovery-scenarios.v1",
        "privacy": "synthetic-test-catalogue",
        "scenarios": [{
            "session_id": "onboarding",
            "execution_surfaces": ["desktop_backend"],
            "journey_steps": ["execute synthetic journey"],
            "expected_domains": ["business.identity"],
            "expected_external_classes": ["secret_store"],
            "completion_assertions": ["synthetic journey completed"],
        }],
    })
    audit = tmp_path / "audit.json"
    _write(audit, {"reconciliation": {
        "unknown_count": 0,
        "blocking_touchpoint_count": 0,
        "incomplete_discovery_session_count": 0,
        "vault_boundary_ready": True,
    }})
    trace = tmp_path / "onboarding.json"
    _write(trace, {
        "schema_version": "tessaris.business-data-runtime-trace.v1",
        "session_id": "onboarding",
        "scenario": "onboarding",
        "surface": "aggregated",
        "required_surfaces": ["desktop_backend"],
        "included_surfaces": ["desktop_backend"],
        "missing_surfaces": [],
        "fragment_sha256": {"desktop_backend": "a" * 64},
        "expected_vault_domains": ["business.identity"],
        "observed_vault_domains": ["business.identity"],
        "missing_vault_domains": [],
        "unexpected_vault_domains": [],
        "expected_external_classes": ["secret_store"],
        "observed_external_classes": [],
        "missing_external_classes": ["secret_store"],
        "unexpected_external_classes": [],
        "event_count": 1,
        "scenario_completed": True,
        "complete": True,
        "release_gate_passed": True,
        "dropped_event_count": 0,
        "unsafe_write_count": 0,
    })
    with pytest.raises(BusinessDataReleaseEvidenceError, match="external_coverage_invalid"):
        build_business_data_release_evidence(
            manifest_path=manifest,
            scenario_catalogue_path=catalogue,
            audit_report_path=audit,
            trace_report_paths=[trace],
        )


def test_release_evidence_rejects_declared_but_blocking_touchpoint(tmp_path):
    manifest = tmp_path / "manifest.json"
    _write(manifest, {
        "schema_version": "tessaris.business-data-manifest.v1",
        "required_discovery_sessions": [
            {"id": "one", "name": "One", "status": "complete"}
        ],
        "touchpoints": [],
    })
    audit = tmp_path / "audit.json"
    _write(audit, {"reconciliation": {
        "unknown_count": 0,
        "blocking_touchpoint_count": 1,
        "incomplete_discovery_session_count": 0,
        "vault_boundary_ready": False,
    }})
    with pytest.raises(
        BusinessDataReleaseEvidenceError,
        match="blocking_business_data_touchpoints",
    ):
        build_business_data_release_evidence(
            manifest_path=manifest,
            scenario_catalogue_path=_catalogue(tmp_path / "scenarios.json", ("one",)),
            audit_report_path=audit,
            trace_report_paths=[],
        )
