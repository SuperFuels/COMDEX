from backend.modules.aion_gateway import (
    PUBLIC_INTENT_GATEWAY_VERSION,
    PublicIntentGatewayRequest,
    build_public_intent_gateway_preview,
    build_public_intent_gateway_summary,
)


def test_public_intent_gateway_version_locked():
    assert PUBLIC_INTENT_GATEWAY_VERSION == "aion.public_intent_gateway.v0.1"


def test_public_intent_gateway_preview_shape():
    preview = build_public_intent_gateway_preview()
    assert preview["ok"] is True
    assert preview["status"] == "public_intent_gateway_preview_ready"
    assert preview["contract_version"] == PUBLIC_INTENT_GATEWAY_VERSION
    assert preview["business_id"] == "home_fixed"
    assert preview["tenant_key"] == "home_fixed_preview"
    assert preview["source"] == "website_form"
    assert preview["request_hash"]
    assert preview["response_hash"]


def test_public_intent_gateway_maps_human_form_to_normalized_intent_preview():
    preview = build_public_intent_gateway_preview(
        PublicIntentGatewayRequest(
            message="Kitchen leak in Albox, can someone come today?",
            location="Albox",
            requested_service="emergency_leak_repair",
        )
    )
    intent = preview["normalized_intent_preview"]
    assert intent["intent_type"] == "public_website_service_enquiry"
    assert intent["raw_message"] == "Kitchen leak in Albox, can someone come today?"
    assert intent["location"] == "Albox"
    assert intent["requested_service"] == "emergency_leak_repair"
    assert intent["normalization_status"] == "preview_only"
    assert intent["human_review_required"] is True
    assert intent["normalized_intent_hash"]


def test_public_intent_gateway_maps_widget_request_to_machine_cart_preview():
    preview = build_public_intent_gateway_preview(
        {
            "business_id": "home_fixed",
            "tenant_key": "home_fixed_preview",
            "source": "website_button",
            "customer_name": "Jane",
            "customer_contact": "jane@example.com",
            "message": "Need roof repair",
            "location": "Zurgena",
            "requested_service": "roof_repair",
            "preferred_window": "tomorrow_morning",
            "max_fiat_price": "250",
            "currency": "EUR",
        }
    )
    cart = preview["machine_cart_request_preview"]
    assert cart["status"] == "machine_cart_request_preview_only"
    assert cart["business_id"] == "home_fixed"
    assert cart["service_key"] == "roof_repair"
    assert cart["location"] == "Zurgena"
    assert cart["requested_window"] == "tomorrow_morning"
    assert cart["max_fiat_price"] == "250"
    assert cart["currency"] == "EUR"
    assert cart["human_review_required"] is True
    assert cart["machine_cart_request_hash"]


def test_public_intent_gateway_returns_human_friendly_quote_preview():
    preview = build_public_intent_gateway_preview()
    quote = preview["human_friendly_quote_preview"]
    assert quote["status"] == "quote_preview_requires_human_review"
    assert "human operator must review" in quote["display_message"]
    assert quote["human_review_required"] is True
    assert quote["final_quote_created"] is False
    assert quote["live_job_created"] is False
    assert quote["payment_created"] is False
    assert quote["escrow_created"] is False


def test_public_intent_gateway_safety_boundary():
    preview = build_public_intent_gateway_preview()
    safety = preview["safety"]
    assert safety["preview_only"] is True
    assert safety["public_gateway_preview"] is True
    assert safety["tenant_validation_required"] is True
    assert safety["signed_request_validation_required"] is True
    assert safety["rate_limiting_required"] is True
    assert safety["abuse_protection_required"] is True
    assert safety["human_review_required"] is True
    assert safety["would_create_booking"] is False
    assert safety["would_create_live_job"] is False
    assert safety["would_execute_goal_engine"] is False
    assert safety["would_move_money"] is False
    assert safety["would_move_pho"] is False
    assert safety["would_require_wallet"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_send_external_message"] is False


def test_public_intent_gateway_blocked_reasons_are_explicit():
    preview = build_public_intent_gateway_preview()
    for reason in [
        "preview_only",
        "tenant_validation_required",
        "signed_request_validation_required",
        "rate_limiting_required",
        "abuse_protection_required",
        "human_review_required",
        "no_live_job_creation",
        "no_booking_side_effect",
        "no_payment_side_effect",
        "no_escrow_side_effect",
        "no_external_message_side_effect",
    ]:
        assert reason in preview["blocked_reasons"]


def test_public_intent_gateway_hash_is_deterministic():
    a = build_public_intent_gateway_preview()
    b = build_public_intent_gateway_preview()
    assert a["request_hash"] == b["request_hash"]
    assert a["response_hash"] == b["response_hash"]


def test_public_intent_gateway_hash_changes_when_message_changes():
    a = build_public_intent_gateway_preview({"message": "Need roof repair"})
    b = build_public_intent_gateway_preview({"message": "Need plumbing repair"})
    assert a["request_hash"] != b["request_hash"]
    assert a["response_hash"] != b["response_hash"]


def test_public_intent_gateway_summary_shape():
    summary = build_public_intent_gateway_summary()
    assert summary["ok"] is True
    assert summary["status"] == "public_intent_gateway_preview_ready"
    assert summary["has_normalized_intent_preview"] is True
    assert summary["has_machine_cart_request_preview"] is True
    assert summary["has_human_friendly_quote_preview"] is True
    assert summary["human_review_required"] is True
    assert summary["preview_only"] is True
    assert summary["would_create_booking"] is False
    assert summary["would_create_live_job"] is False
    assert summary["would_create_payment"] is False
    assert summary["would_create_escrow"] is False
    assert summary["would_send_external_message"] is False
    assert summary["summary_hash"]
