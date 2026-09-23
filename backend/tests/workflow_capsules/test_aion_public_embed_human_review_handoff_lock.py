from backend.modules.aion_gateway.public_embed_human_review_handoff import (
    PUBLIC_EMBED_HUMAN_REVIEW_HANDOFF_VERSION,
    SUPPORTED_REVIEW_DECISIONS,
    build_public_embed_human_review_handoff_preview,
    build_public_embed_human_review_handoff_summary,
)


def test_public_embed_human_review_handoff_version_locked():
    assert (
        PUBLIC_EMBED_HUMAN_REVIEW_HANDOFF_VERSION
        == "aion.public_embed_human_review_handoff.v0.1"
    )


def test_public_embed_human_review_handoff_supported_decisions_locked():
    assert SUPPORTED_REVIEW_DECISIONS == {
        "approve_preview_only",
        "reject_preview_only",
        "request_more_info_preview_only",
        "escalate_preview_only",
    }


def test_public_embed_human_review_handoff_default_shape():
    result = build_public_embed_human_review_handoff_preview()

    assert result["contract_version"] == PUBLIC_EMBED_HUMAN_REVIEW_HANDOFF_VERSION
    assert result["status"] == "waiting_human_review_preview_only"
    assert result["preview_only"] is True
    assert result["business_id"] == "home_fixed"
    assert result["vertical_key"] == "home_repair"
    assert result["request_id"] == "public_embed_request_preview"
    assert result["review_package"]["review_queue"] == "aion_public_embed_human_review"


def test_public_embed_human_review_handoff_preserves_request_context():
    result = build_public_embed_human_review_handoff_preview(
        {
            "business_id": "home_fixed",
            "business_name": "Home Fixed",
            "vertical_key": "home_repair",
            "widget_source": "embedded_chat_widget",
            "request_id": "req_123",
            "customer_message": "I need a quote for a leaking roof in Albox",
            "requested_outcome": "request_quote",
            "service_key": "roof_repair",
            "location": "Albox",
            "currency": "EUR",
        }
    )
    package = result["review_package"]

    assert package["business_id"] == "home_fixed"
    assert package["business_name"] == "Home Fixed"
    assert package["widget_source"] == "embedded_chat_widget"
    assert package["request_id"] == "req_123"
    assert package["customer_message"] == "I need a quote for a leaking roof in Albox"
    assert package["requested_outcome"] == "request_quote"
    assert package["service_key"] == "roof_repair"
    assert package["location"] == "Albox"
    assert package["currency"] == "EUR"


def test_public_embed_human_review_handoff_links_guard_and_mapping_hashes():
    result = build_public_embed_human_review_handoff_preview(
        {
            "normalized_intent_hash": "intent_hash_preview",
            "machine_cart_request_hash": "cart_hash_preview",
            "guard_hash": "guard_hash_preview",
        }
    )
    package = result["review_package"]

    assert package["normalized_intent_hash"] == "intent_hash_preview"
    assert package["machine_cart_request_hash"] == "cart_hash_preview"
    assert package["guard_hash"] == "guard_hash_preview"


def test_public_embed_human_review_handoff_approval_boundary_is_preview_only():
    result = build_public_embed_human_review_handoff_preview()
    boundary = result["approval_boundary"]

    assert boundary["human_review_required"] is True
    assert boundary["human_review_completed"] is False
    assert boundary["approval_decision_recorded"] is False
    assert boundary["approval_can_create_live_job"] is False
    assert boundary["approval_can_execute_goal_engine"] is False
    assert boundary["approval_can_move_money"] is False
    assert boundary["approval_can_send_external_messages"] is False
    assert boundary["next_step"] == "future_guarded_approval_path"


def test_public_embed_human_review_handoff_safety_blocks_side_effects():
    result = build_public_embed_human_review_handoff_preview()
    safety = result["safety"]

    assert safety["preview_only"] is True
    assert safety["public_route_mounted"] is False
    assert safety["unauthenticated_public_write_route_exposed"] is False
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


def test_public_embed_human_review_handoff_hashes_are_stable_for_same_input():
    request = {
        "business_id": "home_fixed",
        "business_name": "Home Fixed",
        "vertical_key": "home_repair",
        "widget_source": "website_form_widget",
        "request_id": "req_123",
        "customer_message": "Leak under sink in Albox",
        "requested_outcome": "request_quote",
        "service_key": "plumbing",
        "location": "Albox",
        "currency": "EUR",
    }

    a = build_public_embed_human_review_handoff_preview(request)
    b = build_public_embed_human_review_handoff_preview(dict(reversed(list(request.items()))))

    assert a["review_package_hash"] == b["review_package_hash"]
    assert a["approval_boundary_hash"] == b["approval_boundary_hash"]
    assert a["safety_hash"] == b["safety_hash"]
    assert a["response_hash"] == b["response_hash"]


def test_public_embed_human_review_handoff_hash_changes_when_message_changes():
    a = build_public_embed_human_review_handoff_preview(
        {"customer_message": "Leak under sink"}
    )
    b = build_public_embed_human_review_handoff_preview(
        {"customer_message": "Roof leak"}
    )

    assert a["review_package_hash"] != b["review_package_hash"]
    assert a["response_hash"] != b["response_hash"]


def test_public_embed_human_review_handoff_summary_shape():
    summary = build_public_embed_human_review_handoff_summary(
        {
            "business_id": "home_fixed",
            "vertical_key": "home_repair",
            "request_id": "req_456",
        }
    )

    assert summary["contract_version"] == PUBLIC_EMBED_HUMAN_REVIEW_HANDOFF_VERSION
    assert summary["status"] == "waiting_human_review_preview_only"
    assert summary["preview_only"] is True
    assert summary["business_id"] == "home_fixed"
    assert summary["vertical_key"] == "home_repair"
    assert summary["request_id"] == "req_456"
    assert summary["has_review_package"] is True
    assert summary["has_approval_boundary"] is True
    assert summary["has_safety"] is True
    assert summary["human_review_required"] is True
    assert summary["human_review_completed"] is False
    assert summary["approval_decision_recorded"] is False
    assert summary["public_route_mounted"] is False
    assert summary["would_create_live_job"] is False
    assert summary["would_execute_goal_engine"] is False
    assert summary["would_move_money"] is False
    assert summary["would_send_external_messages"] is False
    assert summary["next_step"] == "future_guarded_approval_path"
    assert summary["summary_hash"]
