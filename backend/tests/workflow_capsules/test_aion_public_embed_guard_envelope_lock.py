
from backend.modules.aion_gateway.public_embed_guard_envelope import (

    PUBLIC_EMBED_GUARD_ENVELOPE_VERSION,

    build_public_embed_guard_envelope_preview,

    build_public_embed_guard_envelope_summary,

)

def test_public_embed_guard_envelope_version_locked():

    assert PUBLIC_EMBED_GUARD_ENVELOPE_VERSION == "aion.public_embed_guard_envelope.v0.1"

def test_public_embed_guard_envelope_default_preview_shape():

    result = build_public_embed_guard_envelope_preview()

    assert result["contract_version"] == PUBLIC_EMBED_GUARD_ENVELOPE_VERSION

    assert result["status"] == "guard_envelope_preview_ready"

    assert result["preview_only"] is True

    assert result["business_id"] == "home_fixed"

    assert result["vertical_key"] == "home_repair"

    assert result["widget_source"] == "website_form_widget"

    assert result["request_preview"]["preview_only"] is True

def test_public_embed_guard_envelope_records_required_guards():

    result = build_public_embed_guard_envelope_preview()

    guards = result["guards"]

    assert guards["tenant_business_key_validation_required"] is True

    assert guards["tenant_business_key_validated"] is False

    assert guards["signed_request_validation_required"] is True

    assert guards["signed_request_validated"] is False

    assert guards["rate_limiting_required"] is True

    assert guards["rate_limiting_enforced"] is False

    assert guards["abuse_protection_required"] is True

    assert guards["abuse_protection_enforced"] is False

    assert guards["human_review_required"] is True

    assert guards["human_review_completed"] is False

def test_public_embed_guard_envelope_records_present_key_and_signature_without_validating_live():

    result = build_public_embed_guard_envelope_preview(

        {

            "tenant_key": "tenant_preview_key",

            "signature": "sig_preview",

        }

    )

    guards = result["guards"]

    assert guards["tenant_business_key_present"] is True

    assert guards["signature_present"] is True

    assert guards["tenant_business_key_validated"] is False

    assert guards["signed_request_validated"] is False

def test_public_embed_guard_envelope_blocks_unsupported_widget_source():

    result = build_public_embed_guard_envelope_preview(

        {"widget_source": "unsupported_widget_source"}

    )

    assert result["status"] == "blocked_unsupported_widget_source"

    assert "unsupported_widget_source" in result["blocked_reasons"]

def test_public_embed_guard_envelope_safety_flags_block_side_effects():

    result = build_public_embed_guard_envelope_preview()

    safety = result["safety"]

    assert safety["preview_only"] is True

    assert safety["human_review_required"] is True

    assert safety["would_create_booking"] is False

    assert safety["would_create_live_job"] is False

    assert safety["would_execute_goal_engine"] is False

    assert safety["would_move_money"] is False

    assert safety["would_move_pho"] is False

    assert safety["would_require_wallet"] is False

    assert safety["would_create_payment"] is False

    assert safety["would_create_escrow"] is False

    assert safety["would_release_funds"] is False

    assert safety["would_send_external_messages"] is False

    assert safety["unauthenticated_public_write_route_exposed"] is False

    assert safety["public_route_mounted"] is False

def test_public_embed_guard_envelope_hashes_are_stable_for_same_input():

    request = {

        "business_id": "home_fixed",

        "vertical_key": "home_repair",

        "widget_source": "embedded_chat_widget",

        "customer_message": "Leak under sink in Albox",

        "requested_outcome": "request_quote",

    }

    a = build_public_embed_guard_envelope_preview(request)

    b = build_public_embed_guard_envelope_preview(dict(reversed(list(request.items()))))

    assert a["request_hash"] == b["request_hash"]

    assert a["guard_hash"] == b["guard_hash"]

    assert a["safety_hash"] == b["safety_hash"]

    assert a["response_hash"] == b["response_hash"]

def test_public_embed_guard_envelope_hash_changes_when_request_changes():

    a = build_public_embed_guard_envelope_preview({"customer_message": "Leak under sink"})

    b = build_public_embed_guard_envelope_preview({"customer_message": "Roof leak"})

    assert a["request_hash"] != b["request_hash"]

    assert a["response_hash"] != b["response_hash"]

def test_public_embed_guard_envelope_summary_shape():

    summary = build_public_embed_guard_envelope_summary(

        {

            "business_id": "home_fixed",

            "vertical_key": "home_repair",

            "widget_source": "website_button_widget",

        }

    )

    assert summary["contract_version"] == PUBLIC_EMBED_GUARD_ENVELOPE_VERSION

    assert summary["status"] == "guard_envelope_preview_ready"

    assert summary["preview_only"] is True

    assert summary["has_request_preview"] is True

    assert summary["has_guards"] is True

    assert summary["has_safety"] is True

    assert summary["tenant_business_key_validation_required"] is True

    assert summary["signed_request_validation_required"] is True

    assert summary["rate_limiting_required"] is True

    assert summary["abuse_protection_required"] is True

    assert summary["human_review_required"] is True

    assert summary["public_route_mounted"] is False

    assert summary["unauthenticated_public_write_route_exposed"] is False

    assert summary["would_create_live_job"] is False

    assert summary["would_execute_goal_engine"] is False

    assert summary["would_move_money"] is False

    assert summary["summary_hash"]

def test_public_embed_guard_envelope_does_not_create_frontend_visual():

    summary = build_public_embed_guard_envelope_summary()

    assert summary["preview_only"] is True

    assert summary["public_route_mounted"] is False

