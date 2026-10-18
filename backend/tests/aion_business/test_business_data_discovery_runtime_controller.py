from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.modules.aion_business.api.business_data_discovery_runtime_api import (
    create_business_data_discovery_runtime_router,
)
from backend.modules.aion_business.runtime.business_data_discovery_runtime_controller import (
    BusinessDataDiscoveryRuntimeController,
)


ACTIVE_DESTINATION: Path | None = None


def _write() -> None:
    assert ACTIVE_DESTINATION is not None
    ACTIVE_DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_DESTINATION.write_text("synthetic-business-value", encoding="utf-8")


def _controller(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "schema_version": "tessaris.business-data-manifest.v1",
        "required_discovery_sessions": [
            {"id": "business-onboarding", "name": "Onboarding", "status": "required"}
        ],
        "touchpoints": [],
    }), encoding="utf-8")
    return BusinessDataDiscoveryRuntimeController(
        manifest_path=manifest,
        trace_root=tmp_path / "evidence",
        source_root=Path(__file__).resolve().parents[3],
        application_root=tmp_path / "app",
        update_root=tmp_path / "updates",
        vault_roots=[tmp_path / "vault"],
        path_fingerprint_key=b"runtime-controller-fingerprint-key!!",
    )


def test_controller_captures_live_backend_writes_and_returns_content_free_summary(tmp_path):
    global ACTIVE_DESTINATION
    controller = _controller(tmp_path)
    controller.start(session_id="business-onboarding", scenario="onboarding-save")
    ACTIVE_DESTINATION = tmp_path / "vault" / "private-customer-name.json"
    _write()
    result = controller.stop(scenario_completed=True)
    assert result["release_gate_passed"] is True
    assert result["fragment_name"] == "business-onboarding.desktop_backend.json"
    assert result["campaign"]["missing_session_count"] == 1
    encoded = json.dumps(result)
    assert "private-customer-name" not in encoded
    assert "synthetic-business-value" not in encoded
    assert result["customer_content_included"] is False
    assert result["raw_paths_included"] is False


def test_controller_ignores_live_engineering_evidence_written_beneath_trace_root(tmp_path):
    global ACTIVE_DESTINATION
    controller = _controller(tmp_path)
    controller.start(session_id="business-onboarding", scenario="provider-journey")
    ACTIVE_DESTINATION = tmp_path / "evidence" / "provider-sandbox.json"
    _write()
    ACTIVE_DESTINATION = tmp_path / "vault" / "record.json"
    _write()
    result = controller.stop(scenario_completed=True)
    assert result["event_count"] == 2
    assert result["unsafe_write_count"] == 0
    assert result["release_gate_passed"] is True


def test_runtime_api_is_disabled_without_secret_and_rejects_unauthorised_control(tmp_path):
    controller = _controller(tmp_path)
    app = FastAPI()
    app.include_router(create_business_data_discovery_runtime_router(
        controller=controller,
        access_token="engineering-only-secret-token-32-bytes",
    ))
    client = TestClient(app)
    assert client.get("/api/aion/business/discovery-runtime/status").status_code == 401
    response = client.post(
        "/api/aion/business/discovery-runtime/start",
        headers={"X-Tessaris-Discovery-Token": "engineering-only-secret-token-32-bytes"},
        json={"session_id": "business-onboarding", "scenario": "live-onboarding"},
    )
    assert response.status_code == 200
    duplicate = client.post(
        "/api/aion/business/discovery-runtime/start",
        headers={"X-Tessaris-Discovery-Token": "engineering-only-secret-token-32-bytes"},
        json={"session_id": "business-onboarding", "scenario": "duplicate"},
    )
    assert duplicate.status_code == 409
    stopped = client.post(
        "/api/aion/business/discovery-runtime/stop",
        headers={"X-Tessaris-Discovery-Token": "engineering-only-secret-token-32-bytes"},
        json={"scenario_completed": False},
    )
    assert stopped.status_code == 200
    assert stopped.json()["release_gate_passed"] is False
