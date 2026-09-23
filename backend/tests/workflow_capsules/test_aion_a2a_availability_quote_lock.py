from backend.modules.aion_gateway.a2a_availability_quote import (
    A2A_AVAILABILITY_QUOTE_VERSION,
    build_a2a_availability_quote_bundle,
    build_business_availability_preview,
    build_machine_cart_quote_request_preview,
    validate_machine_cart_quote_request_preview,
)


def test_business_availability_preview_has_identity_and_version():
    p = build_business_availability_preview()

    assert p["ok"] is True
    assert p["status"] == "preview_ready"
    assert p["contract_version"] == A2A_AVAILABILITY_QUOTE_VERSION
    assert p["endpoint_key"] == "business_availability"
    assert p["method"] == "GET"
    assert p["business_id"] == "home_fixed"
    assert p["business_name"] == "Home Fixed"
    assert p["vertical_key"] == "home_repair"
    assert p["industry_key"] == "trades"


def test_business_availability_preview_is_universal_and_preview_only():
    p = build_business_availability_preview()

    assert p["universal_gateway"] is True
    assert p["availability_mode"] == "preview_only"
    assert p["availability_state"]["can_accept_request_preview"] is True
    assert p["availability_state"]["can_quote_preview"] is True
    assert p["availability_state"]["can_create_live_booking"] is False
    assert p["availability_state"]["requires_human_review_before_booking"] is True


def test_availability_windows_do_not_allow_booking():
    p = build_business_availability_preview()

    assert len(p["availability_windows"]) >= 1
    for window in p["availability_windows"]:
        assert window["booking_allowed"] is False
        assert window["human_review_required"] is True


def test_quote_request_validation_accepts_required_fields():
    out = validate_machine_cart_quote_request_preview(
        {
            "business_id": "home_fixed",
            "vertical_key": "home_repair",
            "service_id": "inspection_and_quote",
            "requested_outcome": "Need a preview quote",
        }
    )

    assert out["ok"] is True
    assert out["status"] == "valid"
    assert out["missing_fields"] == []


def test_quote_request_validation_blocks_missing_fields():
    out = validate_machine_cart_quote_request_preview({"business_id": "home_fixed"})

    assert out["ok"] is False
    assert out["status"] == "invalid"
    assert "vertical_key" in out["missing_fields"]
    assert "service_id" in out["missing_fields"]
    assert "requested_outcome" in out["missing_fields"]


def test_machine_cart_quote_request_preview_has_post_contract():
    p = build_machine_cart_quote_request_preview()

    assert p["ok"] is True
    assert p["status"] == "preview_ready"
    assert p["contract_version"] == A2A_AVAILABILITY_QUOTE_VERSION
    assert p["endpoint_key"] == "machine_cart_quote_request_preview"
    assert p["method"] == "POST"
    assert p["business_id"] == "home_fixed"
    assert p["vertical_key"] == "home_repair"
    assert p["industry_key"] == "trades"


def test_machine_cart_quote_request_preview_does_not_create_final_quote():
    p = build_machine_cart_quote_request_preview()
    q = p["quote_preview"]

    assert q["status"] == "quote_preview_only"
    assert q["final_quote_created"] is False
    assert q["quote_negotiation_enabled"] is False
    assert q["human_review_required"] is True
    assert q["pricing_mode"] == "requires_human_review"


def test_machine_cart_quote_request_preview_blocks_invalid_request():
    p = build_machine_cart_quote_request_preview({"business_id": "home_fixed"})

    assert p["ok"] is False
    assert p["status"] == "blocked"
    assert p["validation"]["status"] == "invalid"
    assert "vertical_key" in p["blocked_reasons"]


def test_phase_11c_safety_has_no_side_effects():
    for p in [
        build_business_availability_preview(),
        build_machine_cart_quote_request_preview(),
        build_a2a_availability_quote_bundle(),
    ]:
        safety = p["safety"]
        assert safety["guarded"] is True
        assert safety["preview_only"] is True
        assert safety["public_route_exposed"] is False
        assert safety["requires_auth"] is True
        assert safety["human_review_required"] is True
        assert safety["would_execute_workflow"] is False
        assert safety["would_create_booking"] is False
        assert safety["would_move_money"] is False
        assert safety["would_move_pho"] is False
        assert safety["would_create_payment"] is False
        assert safety["would_create_escrow"] is False
        assert safety["would_send_external_message"] is False
        assert safety["quote_negotiation_enabled"] is False
        assert safety["live_booking_supported"] is False


def test_availability_and_quote_hashes_are_stable():
    a1 = build_business_availability_preview()
    a2 = build_business_availability_preview()
    q1 = build_machine_cart_quote_request_preview()
    q2 = build_machine_cart_quote_request_preview()

    assert a1["availability_hash"] == a2["availability_hash"]
    assert q1["quote_request_hash"] == q2["quote_request_hash"]


def test_availability_quote_hashes_change_with_vertical_identity():
    a1 = build_business_availability_preview(vertical_key="home_repair", industry_key="trades")
    a2 = build_business_availability_preview(vertical_key="legal_services", industry_key="professional_services")

    assert a1["availability_hash"] != a2["availability_hash"]


def test_availability_quote_bundle_contains_both_responses():
    b = build_a2a_availability_quote_bundle()

    assert b["ok"] is True
    assert b["status"] == "preview_ready"
    assert b["business_id"] == "home_fixed"
    assert b["vertical_key"] == "home_repair"
    assert b["industry_key"] == "trades"
    assert b["universal_gateway"] is True
    assert b["availability"]["endpoint_key"] == "business_availability"
    assert b["quote_request_preview"]["endpoint_key"] == "machine_cart_quote_request_preview"
    assert b["bundle_hash"]
