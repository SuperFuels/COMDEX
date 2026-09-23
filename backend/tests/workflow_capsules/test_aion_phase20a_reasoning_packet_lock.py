from backend.modules.aion_lrm.reasoning_packet import (
    AION_REASONING_PACKET_VERSION,
    build_aion_reasoning_packet,
    build_home_fixed_reasoning_packet_preview,
)


def test_reasoning_packet_exposes_core_contexts():
    packet = build_home_fixed_reasoning_packet_preview()

    assert packet["packet_version"] == AION_REASONING_PACKET_VERSION
    assert packet["business_id"] == "home_fixed"
    assert packet["vertical_key"] == "home_repair"

    for key in [
        "website_intake",
        "commercial_ticket",
        "workflow_context",
        "agentmap_context",
        "boardroom_context",
        "proof_context",
        "ets_context",
        "safety",
        "reasoning_packet_hash",
        "summary_hash",
    ]:
        assert key in packet


def test_reasoning_packet_is_deterministic():
    a = build_home_fixed_reasoning_packet_preview()
    b = build_home_fixed_reasoning_packet_preview()

    assert a["reasoning_packet_hash"] == b["reasoning_packet_hash"]
    assert a["summary_hash"] == b["summary_hash"]


def test_reasoning_packet_hash_changes_when_meaning_changes():
    a = build_home_fixed_reasoning_packet_preview()
    b = build_aion_reasoning_packet(
        business_id="home_fixed",
        vertical_key="home_repair",
        source="home_fixed_website_widget_preview",
        website_intake={"customer_message": "Broken gate in Albox"},
    )

    assert a["reasoning_packet_hash"] != b["reasoning_packet_hash"]


def test_reasoning_packet_safety_boundary_is_locked():
    packet = build_home_fixed_reasoning_packet_preview()
    safety = packet["safety"]

    assert safety["preview_only"] is True
    assert safety["human_review_required"] is True
    assert safety["booking_created"] is False
    assert safety["payment_created"] is False
    assert safety["escrow_created"] is False
    assert safety["external_message_sent"] is False
    assert safety["live_chain_write"] is False
    assert safety["raw_tool_execution"] is False
    assert safety["automatic_memory_mutation"] is False
    assert safety["goal_engine_executed"] is False
    assert safety["workflow_executed_live"] is False


def test_home_fixed_packet_routes_to_founder_review():
    packet = build_home_fixed_reasoning_packet_preview()

    assert packet["risk_level"] == "human_review_required"
    assert packet["recommended_next_action"] == "show_founder_review_and_proof_preview"
    assert "booking_requires_human_approval" in packet["blocked_reasons"]
    assert packet["boardroom_context"]["human_review_handoff"] is True
