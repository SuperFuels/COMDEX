from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


PATH = "/api/local-node/aion/lrm/pilot-context-preview"


def test_phase21c_preview_endpoint_returns_payload():
    response = client.get(PATH)

    assert response.status_code == 200
    payload = response.json()

    assert payload["payload_type"] == "aion_lrm_pilot_context_payload"
    assert payload["business_id"] == "home-fixed"
    assert payload["mission_id"] == "pilot_demo_pdf_mission"
    assert payload["mission_run_id"] == "pilot_demo_run_preview"
    assert payload["payload_hash"].startswith("lrm_pilot_context_payload_")
    assert payload["summary_hash"].startswith("lrm_pilot_context_payload_summary_")


def test_phase21c_preview_endpoint_exposes_pilot_and_boardroom_projection():
    payload = client.get(PATH).json()

    assert "pilot_cockpit_projection" in payload
    assert "boardroom_projection" in payload
    assert payload["pilot_cockpit_projection"]["mode"] == "preview_only"
    assert payload["boardroom_projection"]["status"] == "preview_only"
    assert payload["boardroom_projection"]["human_review_required"] is True


def test_phase21c_preview_endpoint_is_deterministic():
    first = client.get(PATH).json()
    second = client.get(PATH).json()

    assert first["payload_hash"] == second["payload_hash"]
    assert first["summary_hash"] == second["summary_hash"]


def test_phase21c_preview_endpoint_accepts_query_identity():
    response = client.get(
        PATH,
        params={
            "business_id": "home-fixed",
            "mission_id": "mission_lrm_001",
            "mission_run_id": "run_lrm_001",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["mission_id"] == "mission_lrm_001"
    assert payload["mission_run_id"] == "run_lrm_001"
    assert payload["business_container_root"] == "business/home-fixed/missions/mission_lrm_001/runs/run_lrm_001"


def test_phase21c_preview_endpoint_blocks_live_side_effects():
    payload = client.get(PATH).json()
    safety = payload["safety"]

    assert safety["preview_only"] is True
    assert safety["human_review_required"] is True
    assert safety["pilot_context_payload_grants_live_permission"] is False
    assert safety["would_create_booking"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_send_external_message"] is False
    assert safety["would_write_live_chain"] is False
    assert safety["would_execute_workflow"] is False
    assert safety["live_side_effects_enabled"] is False


def test_phase21c_preview_endpoint_does_not_expose_private_reasoning_or_credentials():
    payload = client.get(PATH).json()
    text = str(payload).lower()

    forbidden_values = [
        "private_cot_value",
        "hidden_reasoning_value",
        "access_token_value",
        "api_key_value",
        "password_value",
        "secret_value",
    ]

    for value in forbidden_values:
        assert value not in text

    assert payload["safety"]["private_chain_of_thought_exposed"] is False
    assert payload["safety"]["hidden_reasoning_exposed"] is False
    assert payload["safety"]["credentials_exposed"] is False
