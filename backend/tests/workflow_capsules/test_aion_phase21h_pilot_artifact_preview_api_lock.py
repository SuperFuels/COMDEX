from fastapi.testclient import TestClient

from backend.main import app


def test_phase21h_pilot_artifact_preview_endpoint_creates_container_artifact():
    client = TestClient(app)

    response = client.post(
        "/api/local-node/aion/pilot/artifact-preview",
        json={
            "business_id": "home-fixed",
            "mission_id": "mission_phase21h",
            "mission_run_id": "run_phase21h",
            "step_id": "step_artifact",
            "artifact_type": "document",
            "artifact_name": "phase21h-preview.md",
            "title": "Phase 21H Preview",
            "content": "Safe backend artifact preview.",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["payload_type"] == "aion_pilot_artifact_preview"
    assert payload["status"] == "draft_preview"
    assert payload["artifact_hash"].startswith("sha256:")
    assert payload["receipt_hash"].startswith("sha256:")
    assert payload["business_container_relative_path"].startswith(
        "business/home-fixed/missions/mission_phase21h/runs/run_phase21h/artifacts/"
    )

    safety = payload["safety"]
    assert safety["preview_only"] is True
    assert safety["live_external_side_effects_enabled"] is False
    assert safety["would_send_external_message"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_booking"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_deploy"] is False
    assert safety["would_write_live_chain"] is False


def test_phase21h_endpoint_rejects_unsafe_artifact_name():
    client = TestClient(app)

    response = client.post(
        "/api/local-node/aion/pilot/artifact-preview",
        json={
            "business_id": "home-fixed",
            "mission_id": "mission_phase21h",
            "mission_run_id": "run_phase21h",
            "step_id": "step_artifact",
            "artifact_type": "document",
            "artifact_name": "../escape.md",
            "title": "Bad",
            "content": "Bad",
        },
    )

    assert response.status_code >= 400
