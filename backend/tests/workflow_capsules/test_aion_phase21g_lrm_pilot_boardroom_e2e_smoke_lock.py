from fastapi.testclient import TestClient
from pathlib import Path

from backend.main import app


APP_JS = Path("desktop/mac/src/app.js")
client = TestClient(app)


def test_phase21g_api_to_payload_smoke():
    response = client.get("/api/local-node/aion/lrm/pilot-context-preview")

    assert response.status_code == 200

    payload = response.json()

    assert payload["payload_type"] == "aion_lrm_pilot_context_payload"
    assert payload["business_id"] == "home-fixed"
    assert payload["mission_id"] == "pilot_demo_pdf_mission"
    assert payload["mission_run_id"] == "pilot_demo_run_preview"
    assert payload["payload_hash"].startswith("lrm_pilot_context_payload_")
    assert payload["summary_hash"].startswith("lrm_pilot_context_payload_summary_")
    assert payload["lrm_state"]["next_review_state"] == "return_to_human_review"
    assert payload["pilot_cockpit_projection"]["status"] == "return_to_human_review"
    assert payload["boardroom_projection"]["status"] == "preview_only"


def test_phase21g_frontend_bridge_exists_and_targets_api():
    text = APP_JS.read_text()

    assert "function getAionLrmPilotContextPreviewUrl" in text
    assert "function applyAionLrmPilotContextPreviewPayload" in text
    assert "async function fetchAionLrmPilotContextPreviewIntoPilotState" in text
    assert "/api/local-node/aion/lrm/pilot-context-preview" in text
    assert "createAionPilotFrontendDraftMission" in text
    assert "fetchAionLrmPilotContextPreviewIntoPilotState" in text


def test_phase21g_pilot_state_receives_lrm_payload_fields():
    text = APP_JS.read_text()

    for term in [
        "lrm_context_status",
        "lrm_pilot_context_payload",
        "lrm_context_payload_hash",
        "lrm_context_summary_hash",
        "lrm_next_review_state",
        "lrm_loop_hash",
        "replay_hash",
        "proof_hash",
        "artifact_hash",
        "receipt_hash",
        "stream_events",
    ]:
        assert term in text


def test_phase21g_pilot_readonly_card_is_mounted():
    text = APP_JS.read_text()

    assert "function renderAionLrmPilotContextReadonlyCard" in text
    assert "data-aion-lrm-pilot-context-card" in text
    assert "data-aion-phase21e-lrm-readonly-card" in text
    assert "${renderAionLrmPilotContextReadonlyCard(pilotState)}" in text
    assert "function renderAionPilotSimpleTaskStream" in text


def test_phase21g_boardroom_projection_panel_is_mounted():
    text = APP_JS.read_text()

    assert "function renderAionLrmBoardroomProjectionPanel" in text
    assert "data-aion-lrm-boardroom-projection-panel" in text
    assert "data-aion-phase21f-lrm-boardroom-projection" in text
    assert "${renderAionLrmBoardroomProjectionPanel(snapshot)}" in text
    assert "function renderBoardroomDashboardView" in text


def test_phase21g_no_live_side_effects_in_api_payload():
    payload = client.get("/api/local-node/aion/lrm/pilot-context-preview").json()
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


def test_phase21g_no_forbidden_live_controls_added_to_frontend_blocks():
    text = APP_JS.read_text()

    phase_blocks = []
    for start_marker, end_marker in [
        ("PHASE 21D LOCK: LRM Pilot Context Preview Fetch Bridge", "END PHASE 21D LOCK"),
        ("PHASE 21E LOCK: Read-only LRM context card in existing Pilot stream", "END PHASE 21E LOCK"),
        ("PHASE 21F LOCK: Read-only LRM Boardroom Projection Panel", "END PHASE 21F LOCK"),
    ]:
        start = text.index(start_marker)
        end = text.index(end_marker, start)
        phase_blocks.append(text[start:end])

    block = "\n".join(phase_blocks)

    forbidden = [
        "data-aion-pilot-live-pay",
        "data-aion-pilot-live-deploy",
        "data-aion-pilot-live-send",
        "data-aion-pilot-live-post",
        "data-aion-pilot-live-book",
        "data-aion-pilot-live-escrow",
        "createEscrow",
        "releaseFunds",
        "sendExternalMessage",
        "executeWorkflow",
        "writeLiveChain",
    ]

    for term in forbidden:
        assert term not in block


def test_phase21g_no_private_reasoning_or_credentials_in_payload():
    payload = client.get("/api/local-node/aion/lrm/pilot-context-preview").json()
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


def test_phase21g_e2e_smoke_chain_terms_are_present():
    text = APP_JS.read_text()

    for term in [
        "getAionLrmPilotContextPreviewUrl",
        "fetchAionLrmPilotContextPreviewIntoPilotState",
        "applyAionLrmPilotContextPreviewPayload",
        "renderAionLrmPilotContextReadonlyCard",
        "renderAionLrmBoardroomProjectionPanel",
        "renderAionPilotSimpleTaskStream",
        "renderBoardroomDashboardView",
    ]:
        assert term in text
