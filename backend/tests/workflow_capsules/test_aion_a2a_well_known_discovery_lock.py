from backend.modules.aion_gateway.a2a_well_known_discovery import (
    A2A_WELL_KNOWN_DISCOVERY_VERSION,
    A2A_WELL_KNOWN_PATHS,
    ACCEPTED_PROTOCOLS,
    build_well_known_discovery_preview,
    build_well_known_discovery_summary,
)


def test_well_known_discovery_contract_version():
    assert A2A_WELL_KNOWN_DISCOVERY_VERSION == "aion.a2a_well_known_discovery.v0.1"


def test_well_known_discovery_paths_are_previewed():
    wrapped = build_well_known_discovery_preview()
    payload = wrapped["payload"]

    assert "/.well-known/aion-agent" in A2A_WELL_KNOWN_PATHS
    assert "/.well-known/ai-agent" in A2A_WELL_KNOWN_PATHS
    assert payload["well_known_paths"] == A2A_WELL_KNOWN_PATHS


def test_well_known_discovery_uses_home_fixed_default_context():
    payload = build_well_known_discovery_preview()["payload"]

    assert payload["business_id"] == "home_fixed"
    assert payload["business_name"] == "Home Fixed"
    assert payload["vertical_key"] == "home_repair"
    assert payload["industry_key"] == "trades"


def test_well_known_discovery_exposes_capability_discovery_preview():
    payload = build_well_known_discovery_preview()["payload"]
    caps = payload["capability_discovery_preview"]

    assert caps["business_capabilities_available"] is True
    assert caps["machine_catalog_available"] is True
    assert caps["availability_preview_available"] is True
    assert caps["quote_request_preview_available"] is True
    assert caps["trust_summary_preview_available"] is True
    assert caps["capability_discovery_route"] == "/api/aion/a2a/home_fixed/business_capabilities"


def test_well_known_discovery_advertises_availability_in_preview_form():
    payload = build_well_known_discovery_preview()["payload"]
    availability = payload["availability_preview"]

    assert availability["status"] == "preview_available"
    assert availability["availability_mode"] == "preview_only"
    assert availability["live_booking_enabled"] is False
    assert availability["live_status_polling_enabled"] is False
    assert availability["human_review_required"] is True


def test_well_known_discovery_advertises_accepted_protocols():
    payload = build_well_known_discovery_preview()["payload"]

    for protocol in [
        "aion.a2a.preview.v0",
        "aion.machine_cart.preview.v0",
        "aion.proof_receipt.preview.v0",
        "aion.trust_summary.preview.v0",
    ]:
        assert protocol in ACCEPTED_PROTOCOLS
        assert protocol in payload["accepted_protocols"]


def test_well_known_discovery_advertises_auth_requirements():
    payload = build_well_known_discovery_preview()["payload"]
    auth = payload["authentication_requirements"]

    assert payload["requires_auth"] is True
    assert payload["auth_mode"] == "api_key_or_signed_agent_preview"
    assert auth["api_key_supported_preview"] is True
    assert auth["signed_agent_supported_preview"] is True
    assert auth["agent_identity_validation_enabled"] is False
    assert auth["scoped_permissions_enabled"] is False


def test_well_known_discovery_does_not_mount_public_route():
    wrapped = build_well_known_discovery_preview()
    payload = wrapped["payload"]

    assert wrapped["preview_only"] is True
    assert wrapped["public_route_mounted"] is False
    assert payload["preview_only"] is True
    assert payload["public_route_mounted"] is False
    assert payload["safety"]["would_expose_public_route"] is False


def test_well_known_discovery_preserves_no_side_effect_safety():
    payload = build_well_known_discovery_preview()["payload"]
    safety = payload["safety"]

    for key in [
        "would_create_booking",
        "would_create_live_job",
        "would_execute_goal_engine",
        "would_bypass_human_review",
        "would_move_money",
        "would_move_pho",
        "would_require_wallet",
        "would_create_payment",
        "would_create_escrow",
        "would_release_funds",
        "would_send_external_messages",
        "live_status_polling_enabled",
    ]:
        assert safety[key] is False


def test_well_known_discovery_hashes_are_deterministic_and_change_with_business():
    first = build_well_known_discovery_preview()
    second = build_well_known_discovery_preview()
    third = build_well_known_discovery_preview(business_id="legal_demo", business_name="Legal Demo", vertical_key="legal_services", industry_key="legal")

    assert first["discovery_hash"] == second["discovery_hash"]
    assert first["response_hash"] == second["response_hash"]
    assert first["discovery_hash"] != third["discovery_hash"]
    assert first["response_hash"] != third["response_hash"]


def test_well_known_discovery_summary_is_compact_and_hashed():
    summary = build_well_known_discovery_summary()

    assert summary["business_id"] == "home_fixed"
    assert summary["vertical_key"] == "home_repair"
    assert summary["accepted_protocol_count"] == len(ACCEPTED_PROTOCOLS)
    assert summary["requires_auth"] is True
    assert summary["public_route_mounted"] is False
    assert summary["preview_only"] is True
    assert summary["discovery_hash"]
    assert summary["summary_hash"]
