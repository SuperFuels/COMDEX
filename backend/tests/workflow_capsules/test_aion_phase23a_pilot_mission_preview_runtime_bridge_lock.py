from fastapi.testclient import TestClient
from pathlib import Path

from backend.main import app

ROUTER = Path("backend/api/local_node_router.py")
client = TestClient(app)


def test_phase23a_mission_preview_endpoint_exists_and_uses_backend_spine():
    text = ROUTER.read_text()

    assert '@router.post("/aion/pilot/mission-preview")' in text
    assert "build_deterministic_mission_plan" in text
    assert "create_mission_plan_approval_matrix" in text
    assert "run_mission_runtime_preview" in text
    assert "compile_live_timeline" in text


def test_phase23a_mission_preview_returns_runtime_payload():
    response = client.post(
        "/api/local-node/aion/pilot/mission-preview",
        json={
            "business_id": "home-fixed",
            "mission_id": "mission_phase23a",
            "mission_run_id": "run_phase23a",
            "user_goal": "produce a marketing plan for home fixed and execute the plan to grow the business",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["payload_type"] == "aion_pilot_mission_preview"
    assert payload["business_id"] == "home-fixed"
    assert payload["mission_id"] == "mission_phase23a"
    assert payload["mission_run_id"] == "run_phase23a"

    assert payload["mission_plan"]["dry_run_only"] is True
    assert payload["mission_plan"]["live_side_effects_enabled"] is False
    assert payload["approval_matrix"]["payload_level_approval_still_required"] is True
    assert payload["runtime_preview"]["live_side_effects_enabled"] is False
    assert payload["timeline"]["timeline_executes_tools"] is False
    assert payload["timeline"]["timeline_mutates_provider_state"] is False
    assert payload["timeline_safety"]["allowed"] is True


def test_phase23a_runtime_completes_safe_steps_or_pauses_before_risk():
    payload = client.post(
        "/api/local-node/aion/pilot/mission-preview",
        json={
            "business_id": "home-fixed",
            "mission_id": "mission_phase23a_steps",
            "mission_run_id": "run_phase23a_steps",
            "user_goal": "build and market Home Fixed",
        },
    ).json()

    assert payload["completed_step_ids"]
    assert payload["runtime_preview"]["completed"] in {True, False}

    if payload["paused_step_id"]:
        assert payload["blocked_reason"]
        assert payload["timeline"]["approval_waits"] >= 1

    assert payload["safety"]["preview_only"] is True
    assert payload["safety"]["live_external_side_effects_enabled"] is False
    assert payload["safety"]["would_create_booking"] is False
    assert payload["safety"]["would_create_payment"] is False
    assert payload["safety"]["would_send_external_message"] is False
    assert payload["safety"]["would_deploy"] is False


def test_phase23a_no_raw_live_execution_terms_in_endpoint():
    block = ROUTER.read_text()
    start = block.index("PHASE 23A LOCK")
    end = block.index("END PHASE 23A LOCK", start)
    endpoint = block[start:end]

    forbidden = [
        "sendExternalMessage(",
        "createBooking(",
        "createPayment(",
        "deployProduction(",
        "publishPost(",
        "createEscrow(",
        "writeLiveChain(",
    ]

    for term in forbidden:
        assert term not in endpoint
