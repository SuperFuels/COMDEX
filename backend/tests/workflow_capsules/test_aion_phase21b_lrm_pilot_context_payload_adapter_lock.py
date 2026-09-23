from backend.modules.aion_lrm.lrm_end_to_end_decision_loop import (
    build_default_home_fixed_lrm_end_to_end_decision_loop,
    build_lrm_end_to_end_decision_loop,
)
from backend.services.aion_mission_mode.lrm_pilot_context_payload_adapter import (
    LRM_PILOT_CONTEXT_PAYLOAD_ADAPTER_VERSION,
    build_default_home_fixed_lrm_pilot_context_payload,
    build_lrm_pilot_context_payload,
)


def test_phase21b_builds_default_payload():
    payload = build_default_home_fixed_lrm_pilot_context_payload()

    assert payload["payload_version"] == LRM_PILOT_CONTEXT_PAYLOAD_ADAPTER_VERSION
    assert payload["payload_type"] == "aion_lrm_pilot_context_payload"
    assert payload["business_id"] == "home-fixed"
    assert payload["payload_hash"].startswith("lrm_pilot_context_payload_")
    assert payload["summary_hash"].startswith("lrm_pilot_context_payload_summary_")


def test_phase21b_links_phase20i_lrm_loop():
    loop = build_default_home_fixed_lrm_end_to_end_decision_loop()
    payload = build_lrm_pilot_context_payload(loop)

    assert payload["source_lrm_loop_hash"] == loop["loop_hash"]
    assert payload["source_lrm_loop_summary_hash"] == loop["summary_hash"]
    assert payload["lrm_state"]["loop_hash"] == loop["loop_hash"]
    assert payload["lrm_state"]["next_review_state"] == "return_to_human_review"


def test_phase21b_projects_to_existing_pilot_cockpit_shape():
    payload = build_default_home_fixed_lrm_pilot_context_payload()
    cockpit = payload["pilot_cockpit_projection"]

    assert cockpit["identity"] == "AION Pilot native runtime executor, not UI automation"
    assert cockpit["mode"] == "preview_only"
    assert cockpit["mission_id"] == payload["mission_id"]
    assert cockpit["mission_run_id"] == payload["mission_run_id"]
    assert cockpit["save_path"].startswith("business/home-fixed/missions/")
    assert cockpit["visible_stream_events"]
    assert cockpit["artifacts"]
    assert "payment" in cockpit["blocked_actions"]
    assert "booking" in cockpit["blocked_actions"]
    assert "escrow" in cockpit["blocked_actions"]


def test_phase21b_projects_to_boardroom_readonly_payload():
    payload = build_default_home_fixed_lrm_pilot_context_payload()
    boardroom = payload["boardroom_projection"]

    assert boardroom["surface"] == "boardroom_dashboard"
    assert boardroom["panel_type"] == "lrm_pilot_context"
    assert boardroom["status"] == "preview_only"
    assert boardroom["human_review_required"] is True
    assert boardroom["loop_hash"] == payload["source_lrm_loop_hash"]
    assert boardroom["recommendation_card_hash"]
    assert boardroom["human_review_decision_hash"]


def test_phase21b_partial_evidence_preserves_request_more_evidence_state():
    loop = build_lrm_end_to_end_decision_loop(
        received_evidence={
            "site_photo": {
                "received": True,
                "evidence_hash": "site_photo_only",
            }
        }
    )
    payload = build_lrm_pilot_context_payload(loop)

    assert payload["lrm_state"]["next_review_state"] == "request_more_evidence"
    assert payload["boardroom_projection"]["next_review_state"] == "request_more_evidence"
    assert payload["pilot_cockpit_projection"]["status"] == "request_more_evidence"


def test_phase21b_uses_business_container_path_hints_only():
    payload = build_default_home_fixed_lrm_pilot_context_payload()

    root = payload["business_container_root"]
    assert root == "business/home-fixed/missions/pilot_demo_pdf_mission/runs/pilot_demo_run_preview"

    for artifact in payload["pilot_cockpit_projection"]["artifacts"]:
        assert artifact["path"].startswith(root)
        assert artifact["status"] == "preview_only"


def test_phase21b_blocks_all_live_side_effects():
    payload = build_default_home_fixed_lrm_pilot_context_payload()
    safety = payload["safety"]

    assert safety["preview_only"] is True
    assert safety["human_review_required"] is True
    assert safety["pilot_context_payload_grants_live_permission"] is False
    assert safety["boardroom_projection_only"] is True
    assert safety["would_create_booking"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_send_external_message"] is False
    assert safety["would_write_live_chain"] is False
    assert safety["would_execute_workflow"] is False
    assert safety["live_side_effects_enabled"] is False


def test_phase21b_redacts_private_reasoning_and_credentials():
    loop = build_default_home_fixed_lrm_end_to_end_decision_loop()
    loop["private_chain_of_thought"] = "PRIVATE_COT_VALUE"
    loop["access_token"] = "ACCESS_TOKEN_VALUE"
    loop["api_key"] = "API_KEY_VALUE"
    loop["hidden_reasoning"] = "HIDDEN_REASONING_VALUE"

    payload = build_lrm_pilot_context_payload(loop)
    text = str(payload)

    assert "PRIVATE_COT_VALUE" not in text
    assert "ACCESS_TOKEN_VALUE" not in text
    assert "API_KEY_VALUE" not in text
    assert "HIDDEN_REASONING_VALUE" not in text
    assert payload["safety"]["private_chain_of_thought_exposed"] is False
    assert payload["safety"]["hidden_reasoning_exposed"] is False
    assert payload["safety"]["credentials_exposed"] is False


def test_phase21b_is_deterministic_for_same_inputs():
    loop = build_default_home_fixed_lrm_end_to_end_decision_loop()

    one = build_lrm_pilot_context_payload(loop)
    two = build_lrm_pilot_context_payload(loop)

    assert one["payload_hash"] == two["payload_hash"]
    assert one["summary_hash"] == two["summary_hash"]
