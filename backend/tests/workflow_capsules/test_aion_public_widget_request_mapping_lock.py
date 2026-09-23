from backend.modules.aion_gateway.public_widget_request_mapping import (
    PUBLIC_WIDGET_REQUEST_MAPPING_VERSION,
    build_public_widget_request_mapping_preview,
    build_public_widget_request_mapping_summary,
)


def _payload():
    return {
        "business_id": "home_fixed",
        "business_name": "Home Fixed",
        "vertical_key": "home_repair",
        "customer_message": "Need a plumber in Albox tomorrow afternoon",
        "requested_service_key": "emergency_leak_repair",
        "requested_location": "Albox",
        "requested_window": "tomorrow_afternoon",
        "max_fiat_price": "180.00",
        "currency": "EUR",
    }


def test_public_widget_mapping_version_locked():
    assert PUBLIC_WIDGET_REQUEST_MAPPING_VERSION == "aion.public_widget_request_mapping.v0.1"


def test_website_form_maps_to_normalized_intent_preview():
    result = build_public_widget_request_mapping_preview(
        widget_surface="website_form_widget_preview",
        payload=_payload(),
    )

    assert result["ok"] is True
    assert result["status"] == "widget_request_mapping_preview_ready"
    assert result["widget_surface"] == "website_form_widget_preview"
    assert result["mapping_kind"] == "human_form_to_normalized_inbound_intent"
    assert result["normalized_intent_preview"]["status"] == "normalized_intent_preview_only"
    assert result["normalized_intent_preview"]["requested_service_key"] == "emergency_leak_repair"
    assert result["normalized_intent_preview"]["requested_location"] == "Albox"
    assert result["normalized_intent_preview"]["human_review_required"] is True
    assert result["normalized_intent_preview"]["live_intent_created"] is False


def test_website_button_maps_to_machine_cart_request_preview():
    result = build_public_widget_request_mapping_preview(
        widget_surface="website_button_widget_preview",
        payload=_payload(),
    )

    assert result["ok"] is True
    assert result["widget_surface"] == "website_button_widget_preview"
    assert result["mapping_kind"] == "button_request_to_machine_cart_request"
    assert result["machine_cart_request_preview"]["status"] == "machine_cart_request_preview_only"
    assert result["machine_cart_request_preview"]["service_key"] == "emergency_leak_repair"
    assert result["machine_cart_request_preview"]["location"] == "Albox"
    assert result["machine_cart_request_preview"]["quote_preview_only"] is True
    assert result["machine_cart_request_preview"]["live_cart_created"] is False


def test_embedded_chat_maps_to_preview_intent_or_cart():
    result = build_public_widget_request_mapping_preview(
        widget_surface="embedded_chat_widget_preview",
        payload=_payload(),
    )

    assert result["ok"] is True
    assert result["widget_surface"] == "embedded_chat_widget_preview"
    assert result["mapping_kind"] == "chat_request_to_normalized_intent_or_machine_cart_request"
    assert result["normalized_intent_preview"]["source_surface"] == "embedded_chat_widget_preview"
    assert result["machine_cart_request_preview"]["source_surface"] == "embedded_chat_widget_preview"


def test_surface_aliases_are_supported():
    form = build_public_widget_request_mapping_preview(widget_surface="form", payload=_payload())
    button = build_public_widget_request_mapping_preview(widget_surface="button", payload=_payload())
    chat = build_public_widget_request_mapping_preview(widget_surface="chat", payload=_payload())

    assert form["widget_surface"] == "website_form_widget_preview"
    assert button["widget_surface"] == "website_button_widget_preview"
    assert chat["widget_surface"] == "embedded_chat_widget_preview"


def test_unsupported_surface_is_blocked():
    result = build_public_widget_request_mapping_preview(
        widget_surface="unknown_widget",
        payload=_payload(),
    )

    assert result["ok"] is False
    assert result["status"] == "unsupported_widget_surface"
    assert "unsupported_widget_surface" in result["blocked_reasons"]
    assert result["safety"]["preview_only"] is True
    assert result["safety"]["would_create_live_job"] is False


def test_required_guards_are_present():
    result = build_public_widget_request_mapping_preview(
        widget_surface="website_form_widget_preview",
        payload=_payload(),
    )

    guards = result["required_guards"]
    assert guards["tenant_business_key_validation_required"] is True
    assert guards["signed_request_validation_required"] is True
    assert guards["rate_limiting_required"] is True
    assert guards["abuse_protection_required"] is True
    assert guards["human_review_required"] is True


def test_public_intent_gateway_preview_is_guarded():
    result = build_public_widget_request_mapping_preview(
        widget_surface="website_form_widget_preview",
        payload=_payload(),
    )

    gateway = result["public_intent_gateway_preview"]
    assert gateway["status"] == "public_intent_gateway_preview_only"
    assert gateway["gateway_contract"] == "aion.public_intent_gateway.v0.1"
    assert gateway["tenant_business_key_validation_required"] is True
    assert gateway["signed_request_validation_required"] is True
    assert gateway["rate_limiting_required"] is True
    assert gateway["abuse_protection_required"] is True
    assert gateway["unauthenticated_public_write_route_exposed"] is False


def test_hashes_are_deterministic_and_change_with_payload():
    a = build_public_widget_request_mapping_preview(
        widget_surface="website_form_widget_preview",
        payload=_payload(),
    )
    b = build_public_widget_request_mapping_preview(
        widget_surface="website_form_widget_preview",
        payload=dict(reversed(list(_payload().items()))),
    )

    changed = _payload()
    changed["requested_location"] = "Zurgena"
    c = build_public_widget_request_mapping_preview(
        widget_surface="website_form_widget_preview",
        payload=changed,
    )

    assert a["request_hash"] == b["request_hash"]
    assert a["normalized_intent_hash"] == b["normalized_intent_hash"]
    assert a["machine_cart_request_hash"] == b["machine_cart_request_hash"]
    assert a["response_hash"] == b["response_hash"]
    assert a["response_hash"] != c["response_hash"]


def test_safety_flags_block_live_side_effects():
    result = build_public_widget_request_mapping_preview(
        widget_surface="website_button_widget_preview",
        payload=_payload(),
    )

    safety = result["safety"]
    assert safety["preview_only"] is True
    assert safety["human_review_required"] is True
    assert safety["would_create_booking"] is False
    assert safety["would_create_live_job"] is False
    assert safety["would_execute_goal_engine"] is False
    assert safety["would_bypass_human_review"] is False
    assert safety["would_move_money"] is False
    assert safety["would_move_pho"] is False
    assert safety["would_require_wallet"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_release_funds"] is False
    assert safety["would_send_external_messages"] is False
    assert safety["would_expose_unauthenticated_public_write_route"] is False


def test_summary_reports_presence_and_safety():
    summary = build_public_widget_request_mapping_summary(
        widget_surface="embedded_chat_widget_preview",
        payload=_payload(),
    )

    assert summary["ok"] is True
    assert summary["preview_only"] is True
    assert summary["has_normalized_intent_preview"] is True
    assert summary["has_machine_cart_request_preview"] is True
    assert summary["has_public_intent_gateway_preview"] is True
    assert summary["human_review_required"] is True
    assert summary["would_create_booking"] is False
    assert summary["would_create_live_job"] is False
    assert summary["would_execute_goal_engine"] is False
    assert summary["would_move_money"] is False
    assert summary["would_create_payment"] is False
    assert summary["would_create_escrow"] is False
    assert summary["would_send_external_message"] is False
    assert "summary_hash" in summary
