from __future__ import annotations

from backend.modules.aion_gateway.agent_channels import (
    AGENT_CHANNEL_PROTOCOL_VERSION,
    SUPPORTED_AGENT_CHANNELS,
    build_agent_inbox_message,
    list_agent_channels,
    preview_agent_channel_message,
)


def test_agent_channel_protocol_version_locked():
    assert AGENT_CHANNEL_PROTOCOL_VERSION == "aion.agent_channels.v0.1"


def test_supported_agent_channels_are_reserved():
    expected = {
        "agent_email",
        "agent_phone",
        "whatsapp",
        "embedded_chat",
        "supplier_email",
        "booking_inbox",
    }
    assert expected.issubset(SUPPORTED_AGENT_CHANNELS)


def test_list_agent_channels_returns_all_channels():
    out = list_agent_channels()
    assert out["ok"] is True
    assert out["count"] >= 6
    keys = {row["channel_key"] for row in out["channels"]}
    assert "agent_email" in keys
    assert "supplier_email" in keys


def test_agent_email_message_normalizes_into_intent_preview():
    out = preview_agent_channel_message(
        business_id="home_fixed",
        channel_key="agent_email",
        raw_subject="Leaking roof repair",
        raw_body="Customer needs roof repair in Albox.",
        sender_ref="customer@example.com",
        metadata={"vertical_key": "home_repair"},
    )

    assert out["ok"] is True
    assert out["routing_status"] == "preview_ready"
    assert out["blocked_reasons"] == []
    assert out["normalized_intent_preview"]["business_id"] == "home_fixed"
    assert out["normalized_intent_preview"]["source_channel"] == "agent_email"
    assert out["normalized_intent_preview"]["vertical_key"] == "home_repair"
    assert out["normalized_intent_preview"]["intent_type"] == "customer_request"
    assert out["dry_run_only"] is True
    assert out["requires_human_review"] is True


def test_supplier_message_can_attach_to_job_timeline_preview():
    out = preview_agent_channel_message(
        business_id="home_fixed",
        channel_key="supplier_email",
        raw_subject="Materials ready",
        raw_body="Tiles and grout ready for collection.",
        sender_ref="supplier@example.com",
        job_id="job_home_fixed_001",
    )

    assert out["ok"] is True
    assert out["normalized_intent_preview"]["intent_type"] == "supplier_update"
    assert out["timeline_preview"]["would_attach_to_job_id"] == "job_home_fixed_001"
    assert out["timeline_preview"]["append_only_preview"] is True
    assert out["timeline_preview"]["would_mutate_job_timeline"] is False


def test_unsupported_channel_blocks():
    out = preview_agent_channel_message(
        business_id="home_fixed",
        channel_key="telegram",
        raw_subject="Hello",
    )

    assert out["ok"] is False
    assert out["routing_status"] == "blocked"
    assert "unsupported_channel" in out["blocked_reasons"]


def test_reserved_channel_blocks_for_now():
    out = preview_agent_channel_message(
        business_id="home_fixed",
        channel_key="whatsapp",
        raw_subject="Need repair",
        raw_body="Customer needs help.",
    )

    assert out["ok"] is False
    assert "channel_reserved_only" in out["blocked_reasons"]


def test_missing_message_content_blocks():
    out = preview_agent_channel_message(
        business_id="home_fixed",
        channel_key="agent_email",
    )

    assert out["ok"] is False
    assert "missing_message_content" in out["blocked_reasons"]


def test_message_hash_is_stable_for_same_payload_shape():
    first = build_agent_inbox_message(
        message_id="m1",
        business_id="home_fixed",
        channel_key="agent_email",
        raw_subject="Leak",
        raw_body="Kitchen leak",
        sender_ref="a@example.com",
    )
    second = build_agent_inbox_message(
        message_id="m1",
        business_id="home_fixed",
        channel_key="agent_email",
        raw_subject="Leak",
        raw_body="Kitchen leak",
        sender_ref="a@example.com",
    )

    assert first["message_hash"] == second["message_hash"]


def test_no_external_sends_calls_or_mutations():
    out = preview_agent_channel_message(
        business_id="home_fixed",
        channel_key="agent_email",
        raw_subject="Leak",
        raw_body="Kitchen leak",
    )

    assert out["would_send_email"] is False
    assert out["would_send_whatsapp"] is False
    assert out["would_call_phone_provider"] is False
    assert out["would_mutate_job_timeline"] is False
    assert out["would_create_external_side_effect"] is False
