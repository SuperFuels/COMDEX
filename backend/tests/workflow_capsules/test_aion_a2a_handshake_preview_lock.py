from backend.modules.aion_gateway.a2a_handshake_preview import (
    A2A_HANDSHAKE_PREVIEW_VERSION,
    build_a2a_handshake_preview,
    build_a2a_handshake_preview_bundle,
    build_a2a_handshake_preview_summary,
    build_a2a_live_status_polling_preview,
    build_a2a_quote_negotiation_preview,
)


def _request():
    return {
        "requesting_agent_id": "agent_google_preview_001",
        "requesting_agent_name": "Google Agent Preview",
        "requested_protocol": "aion.a2a.preview.v0",
        "business_id": "home_fixed",
        "business_name": "Home Fixed",
        "vertical_key": "home_repair",
        "industry_key": "trades",
        "intent_type": "service_request_preview",
        "service_id": "emergency_leak_repair",
        "requested_outcome": "stop active leak",
        "target_price": 180,
        "currency": "EUR",
        "job_id": "home_fixed_job_preview_001",
    }


def test_a2a_handshake_preview_contract_version():
    payload = build_a2a_handshake_preview(_request())
    assert payload["contract_version"] == A2A_HANDSHAKE_PREVIEW_VERSION
    assert payload["status"] == "handshake_preview_only"
    assert payload["business_id"] == "home_fixed"
    assert payload["vertical_key"] == "home_repair"


def test_a2a_handshake_preview_is_guarded_and_not_accepted():
    payload = build_a2a_handshake_preview(_request())
    assert payload["requires_auth"] is True
    assert payload["auth_mode"] == "api_key_or_signed_agent_preview"
    assert payload["agent_identity_validation_enabled"] is False
    assert payload["scoped_permissions_enabled"] is False
    assert payload["handshake_accepted"] is False
    assert payload["handshake_preview_only"] is True


def test_a2a_handshake_preview_lists_protocols_and_hash():
    payload = build_a2a_handshake_preview(_request())
    assert "aion.a2a.preview.v0" in payload["accepted_protocols"]
    assert "aion.machine_cart.preview.v0" in payload["accepted_protocols"]
    assert "aion.quote_negotiation.preview.v0" in payload["accepted_protocols"]
    assert "aion.live_status_polling.preview.v0" in payload["accepted_protocols"]
    assert payload["handshake_hash"]


def test_quote_negotiation_preview_blocks_live_negotiation():
    payload = build_a2a_quote_negotiation_preview(_request())
    assert payload["status"] == "quote_negotiation_preview_only"
    assert payload["quote_negotiation_enabled"] is False
    assert payload["counter_offer_enabled"] is False
    assert payload["final_quote_created"] is False
    assert payload["pricing_mode"] == "requires_human_review"
    assert payload["route_hint"] == "future_guarded_approval_path"
    assert payload["quote_negotiation_hash"]


def test_live_status_polling_preview_blocks_polling():
    payload = build_a2a_live_status_polling_preview(_request())
    assert payload["status"] == "live_status_polling_preview_only"
    assert payload["current_stage"] == "waiting_human_review"
    assert payload["live_status_polling_enabled"] is False
    assert payload["public_status_stream_enabled"] is False
    assert payload["status_polling_hash"]


def test_bundle_contains_all_phase_11i_sections():
    bundle = build_a2a_handshake_preview_bundle(_request())
    assert bundle["status"] == "a2a_handshake_preview_bundle_ready"
    assert bundle["handshake"]
    assert bundle["quote_negotiation"]
    assert bundle["live_status_polling"]
    assert bundle["bundle_hash"]


def test_bundle_keeps_everything_preview_only():
    bundle = build_a2a_handshake_preview_bundle(_request())
    assert bundle["preview_only"] is True
    assert bundle["guarded"] is True
    assert bundle["human_review_required"] is True
    assert bundle["real_a2a_handshake_enabled"] is False
    assert bundle["quote_negotiation_enabled"] is False
    assert bundle["live_status_polling_enabled"] is False


def test_safety_blocks_all_live_side_effects():
    bundle = build_a2a_handshake_preview_bundle(_request())
    safety = bundle["safety"]
    assert safety["would_execute_workflow"] is False
    assert safety["would_create_booking"] is False
    assert safety["would_create_live_job"] is False
    assert safety["would_move_money"] is False
    assert safety["would_move_pho"] is False
    assert safety["would_require_wallet"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_release_funds"] is False
    assert safety["would_send_external_message"] is False
    assert safety["public_route_exposed"] is False


def test_summary_reports_presence_and_hashes():
    summary = build_a2a_handshake_preview_summary(_request())
    assert summary["has_handshake_preview"] is True
    assert summary["has_quote_negotiation_preview"] is True
    assert summary["has_live_status_polling_preview"] is True
    assert summary["bundle_hash"]
    assert summary["summary_hash"]


def test_missing_required_fields_are_reported():
    payload = build_a2a_handshake_preview({})
    assert "requesting_agent_id" in payload["missing_fields"]
    assert "requesting_agent_name" in payload["missing_fields"]
    assert "business_id" in payload["missing_fields"]
