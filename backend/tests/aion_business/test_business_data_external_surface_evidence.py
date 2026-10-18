from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.aion_business.api.business_data_discovery_runtime_api import (
    create_business_data_external_surface_router,
)
from backend.modules.aion_business.runtime.business_data_external_surface_controller import (
    BusinessDataExternalSurfaceController,
    BusinessDataExternalSurfaceControllerError,
)

from backend.modules.aion_business.runtime.business_data_external_surface_evidence import (
    BusinessDataExternalSurfaceEvidenceError,
    BusinessDataExternalSurfaceEvidenceRecorder,
)


ROOT = Path(__file__).resolve().parents[3]


def test_provider_surface_evidence_is_content_free_and_requires_declared_class_coverage(tmp_path):
    recorder = BusinessDataExternalSurfaceEvidenceRecorder(
        manifest_path=ROOT / "config/business-data-manifest.v1.json",
        scenario_catalogue_path=ROOT / "config/business-data-discovery-scenarios.v1.json",
        session_id="lead-booking-intake",
        scenario="lead-booking-intake",
        surface="provider_sandbox",
        fingerprint_key=b"external-surface-fingerprint-key-32!!",
    )
    recorder.record(
        operation="provider.lead.received",
        external_class="provider_api",
        identifier="https://provider.example/private/customer/123",
        approved=True,
    )
    target = tmp_path / "lead-booking-intake.provider_sandbox.json"
    report = recorder.write_report(target, scenario_completed=True)
    assert report["release_gate_passed"] is True
    encoded = target.read_text(encoding="utf-8")
    assert "provider.example" not in encoded
    assert "customer/123" not in encoded
    assert report["observed_external_classes"] == ["provider_api"]
    assert target.stat().st_mode & 0o777 == 0o600


def test_external_surface_fails_closed_for_unknown_destination_or_missing_class(tmp_path):
    recorder = BusinessDataExternalSurfaceEvidenceRecorder(
        manifest_path=ROOT / "config/business-data-manifest.v1.json",
        scenario_catalogue_path=ROOT / "config/business-data-discovery-scenarios.v1.json",
        session_id="email-communications",
        scenario="email-communications",
        surface="provider_sandbox",
        fingerprint_key=b"external-surface-fingerprint-key-32!!",
    )
    recorder.record(
        operation="provider.email.draft",
        external_class="provider_api",
        identifier="gmail-draft-id",
        approved=False,
    )
    report = recorder.report(scenario_completed=True)
    assert report["release_gate_passed"] is False
    assert report["unsafe_write_count"] == 1
    assert report["observed_external_classes"] == ["provider_api"]
    with pytest.raises(BusinessDataExternalSurfaceEvidenceError, match="class_undeclared"):
        recorder.record(
            operation="provider.other",
            external_class="customer_export",
            identifier="unexpected",
            approved=True,
        )


def test_external_controller_accepts_only_fingerprinted_content_free_events(tmp_path):
    controller = BusinessDataExternalSurfaceController(
        manifest_path=ROOT / "config/business-data-manifest.v1.json",
        scenario_catalogue_path=ROOT / "config/business-data-discovery-scenarios.v1.json",
        trace_root=tmp_path,
        fingerprint_key=b"external-controller-fingerprint-key!!",
    )
    status = controller.start(
        session_id="lead-booking-intake",
        scenario="lead-booking-intake",
        surface="provider_sandbox",
    )
    assert status["raw_identifiers_accepted"] is False
    event = controller.record(
        surface="provider_sandbox",
        operation="provider.lead.received",
        external_class="provider_api",
        identifier_hmac_sha256="a" * 64,
        approved=True,
    )
    assert event["event_count"] == 1
    result = controller.stop(surface="provider_sandbox", scenario_completed=True)
    assert result["release_gate_passed"] is True
    evidence = json.loads(
        (tmp_path / result["fragment_name"]).read_text(encoding="utf-8")
    )
    assert evidence["events"][0]["destination_hmac_sha256"] == "a" * 64
    assert set(evidence["events"][0]) == {
        "operation",
        "external_class",
        "destination_class",
        "destination_hmac_sha256",
        "source_path",
        "line",
    }
    with pytest.raises(BusinessDataExternalSurfaceControllerError, match="not_active"):
        controller.record(
            surface="provider_sandbox",
            operation="provider.lead.received",
            external_class="provider_api",
            identifier_hmac_sha256="b" * 64,
            approved=True,
        )


def test_external_surface_api_is_secret_authenticated_and_rejects_raw_identifiers(tmp_path):
    token = "external-evidence-controller-token-32-bytes"
    controller = BusinessDataExternalSurfaceController(
        manifest_path=ROOT / "config/business-data-manifest.v1.json",
        scenario_catalogue_path=ROOT / "config/business-data-discovery-scenarios.v1.json",
        trace_root=tmp_path,
        fingerprint_key=b"external-api-fingerprint-key-32-bytes!!",
    )
    app = FastAPI()
    app.include_router(create_business_data_external_surface_router(
        controller=controller,
        access_token=token,
    ))
    client = TestClient(app)
    prefix = "/api/aion/business/discovery-runtime/external"
    assert client.get(f"{prefix}/status").status_code == 401
    headers = {"X-Tessaris-Discovery-Token": token}
    started = client.post(
        f"{prefix}/start",
        headers=headers,
        json={
            "session_id": "field-mobile",
            "scenario": "field-mobile",
            "surface": "mobile_companion",
        },
    )
    assert started.status_code == 200
    rejected = client.post(
        f"{prefix}/event",
        headers=headers,
        json={
            "surface": "mobile_companion",
            "operation": "mobile.notification.received",
            "external_class": "notification_provider",
            "identifier_hmac_sha256": "c" * 64,
            "approved": True,
            "raw_identifier": "private-mobile-device-id",
        },
    )
    assert rejected.status_code == 422
    accepted = client.post(
        f"{prefix}/event",
        headers=headers,
        json={
            "surface": "mobile_companion",
            "operation": "mobile.notification.received",
            "external_class": "notification_provider",
            "identifier_hmac_sha256": "c" * 64,
            "approved": True,
        },
    )
    assert accepted.status_code == 200
    stopped = client.post(
        f"{prefix}/stop",
        headers=headers,
        json={"surface": "mobile_companion", "scenario_completed": True},
    )
    assert stopped.status_code == 200
    assert stopped.json()["release_gate_passed"] is True
    report = (tmp_path / "field-mobile.mobile_companion.json").read_text(encoding="utf-8")
    assert "private-mobile-device-id" not in report
