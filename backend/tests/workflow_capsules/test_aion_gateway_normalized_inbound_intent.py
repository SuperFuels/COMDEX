from backend.modules.aion_gateway.inbound_gateway import (
    preview_inbound_gateway_intent,
    stable_intent_hash,
)
from backend.modules.aion_gateway.safety import assert_dry_run_only


def _payload():
    return {
        "name": "Kevin",
        "email": "kevin@example.com",
        "phone": "+34 000 000 000",
        "message": "Need a plumber in Arboleas",
        "requested_outcome": "Fix leaking pipe",
    }


def test_legacy_web_form_normalizes_to_preview_contract():
    result = preview_inbound_gateway_intent(
        business_id="BIZ_123",
        source_channel="legacy_web_form",
        vertical_key="plumber",
        intent_type="service_request",
        raw_payload=_payload(),
        gateway_session_id="sess_001",
        trace_context={"trace_id": "trace_001"},
    )

    assert result["ok"] is True

    intent = result["normalized_inbound_intent"]
    preview = result["fulfilment_job_preview"]
    trace = result["machine_trace"]

    assert intent["gateway_protocol_version"] == "aion.gateway.v0.1"
    assert intent["gateway_session_id"] == "sess_001"
    assert intent["trace_context"]["trace_id"] == "trace_001"
    assert intent["business_id"] == "BIZ_123"
    assert intent["source_channel"] == "legacy_web_form"
    assert intent["vertical_key"] == "plumber"
    assert intent["intent_type"] == "service_request"
    assert intent["raw_payload"]["message"] == "Need a plumber in Arboleas"
    assert intent["normalized_payload"]["summary"] == "Need a plumber in Arboleas"
    assert intent["dry_run_only"] is True
    assert intent["requires_human_review"] is True

    assert preview["would_create_fulfilment_job"] is False
    assert preview["would_execute_goal_engine"] is False
    assert preview["requires_human_review"] is True

    assert trace["dry_run_only"] is True
    assert trace["would_write_externally"] is False
    assert trace["would_mutate_business_state"] is False
    assert trace["would_grant_permission"] is False


def test_agent_protocol_normalizes_to_preview_contract():
    result = preview_inbound_gateway_intent(
        business_id="biz_agent",
        source_channel="agent_protocol",
        vertical_key="handyman",
        intent_type="quote_request",
        raw_payload={"message": "Quote for pergola repair"},
    )

    assert result["ok"] is True
    assert result["normalized_inbound_intent"]["source_channel"] == "agent_protocol"
    assert result["fulfilment_job_preview"]["routing_status"] == "preview_ready"


def test_missing_business_id_blocks_preview():
    result = preview_inbound_gateway_intent(
        business_id="",
        source_channel="legacy_web_form",
        vertical_key="plumber",
        intent_type="service_request",
        raw_payload=_payload(),
    )

    assert result["ok"] is False
    assert "missing_business_id" in result["blocked_reasons"]


def test_missing_raw_payload_blocks_preview():
    result = preview_inbound_gateway_intent(
        business_id="biz_123",
        source_channel="legacy_web_form",
        vertical_key="plumber",
        intent_type="service_request",
        raw_payload={},
    )

    assert result["ok"] is False
    assert "missing_raw_payload" in result["blocked_reasons"]


def test_unsupported_source_channel_blocks_preview():
    result = preview_inbound_gateway_intent(
        business_id="biz_123",
        source_channel="whatsapp",
        vertical_key="plumber",
        intent_type="service_request",
        raw_payload=_payload(),
    )

    assert result["ok"] is False
    assert "unsupported_source_channel" in result["blocked_reasons"]


def test_intent_hash_is_order_independent():
    left = stable_intent_hash(
        gateway_protocol_version="aion.gateway.v0.1",
        business_id="BIZ_123",
        source_channel="LEGACY_WEB_FORM",
        intent_type="SERVICE_REQUEST",
        normalized_payload={"b": 2, "a": 1},
    )
    right = stable_intent_hash(
        gateway_protocol_version="aion.gateway.v0.1",
        business_id="biz_123",
        source_channel="legacy_web_form",
        intent_type="service_request",
        normalized_payload={"a": 1, "b": 2},
    )

    assert left == right


def test_intent_hash_excludes_raw_payload():
    expected_summary = "same cleaned intent"

    first = preview_inbound_gateway_intent(
        business_id="biz_123",
        source_channel="legacy_web_form",
        vertical_key="plumber",
        intent_type="service_request",
        raw_payload={"message": "same cleaned intent", "noise": "one"},
    )
    second = preview_inbound_gateway_intent(
        business_id="biz_123",
        source_channel="legacy_web_form",
        vertical_key="plumber",
        intent_type="service_request",
        raw_payload={"message": "same cleaned intent", "noise": "two"},
    )

    assert first["normalized_inbound_intent"]["normalized_payload"]["summary"] == expected_summary
    assert second["normalized_inbound_intent"]["normalized_payload"]["summary"] == expected_summary
    assert first["normalized_inbound_intent"]["normalized_payload"]["vertical_key"] == "plumber"
    assert first["normalized_inbound_intent"]["normalized_payload"]["intent_type"] == "service_request"
    assert first["normalized_inbound_intent"]["intent_hash"] == second["normalized_inbound_intent"]["intent_hash"]


def test_intent_hash_includes_gateway_protocol_version():
    old = stable_intent_hash(
        gateway_protocol_version="aion.gateway.v0.1",
        business_id="biz_123",
        source_channel="legacy_web_form",
        intent_type="service_request",
        normalized_payload={"summary": "x"},
    )
    new = stable_intent_hash(
        gateway_protocol_version="aion.gateway.v0.2",
        business_id="biz_123",
        source_channel="legacy_web_form",
        intent_type="service_request",
        normalized_payload={"summary": "x"},
    )

    assert old != new


def test_raw_payload_and_normalized_payload_stay_separate():
    result = preview_inbound_gateway_intent(
        business_id="biz_123",
        source_channel="legacy_web_form",
        vertical_key="plumber",
        intent_type="service_request",
        raw_payload={"message": "Need help", "untrusted_html": "<script>x</script>"},
    )

    intent = result["normalized_inbound_intent"]
    assert "untrusted_html" in intent["raw_payload"]
    assert "untrusted_html" not in intent["normalized_payload"]


def test_dry_run_guard_raises_runtime_error():
    try:
        assert_dry_run_only(dry_run_only=True, attempted_action="provider_call")
    except RuntimeError as exc:
        assert "blocked forbidden dry-run action" in str(exc)
    else:
        raise AssertionError("provider_call should be blocked in dry-run mode")
