import json

from backend.modules.aion_lrm.reasoning_replay_trace import (
    REASONING_REPLAY_TRACE_VERSION,
    build_default_home_fixed_reasoning_replay_trace,
    build_reasoning_replay_trace,
)


def test_phase20c_builds_default_replay_trace():
    trace = build_default_home_fixed_reasoning_replay_trace()

    assert trace["trace_version"] == REASONING_REPLAY_TRACE_VERSION
    assert trace["trace_type"] == "aion_lrm_reasoning_replay_trace"
    assert trace["runtime"] == "aion_lrm"
    assert trace["preview_only"] is True
    assert trace["safety"]["human_review_required"] is True
    assert trace["replay_trace_hash"].startswith("reasoning_replay_trace_")
    assert trace["summary_hash"].startswith("reasoning_replay_summary_")


def test_phase20c_replay_uses_governed_packet_and_memory_snapshot_hashes():
    packet = {
        "reasoning_packet_hash": "reasoning_packet_abc",
        "website_intake": {"service": "roof repair"},
    }
    snapshot = {
        "snapshot_hash": "reasoning_memory_snapshot_abc",
        "source_reasoning_packet_hash": "reasoning_packet_abc",
        "agentmap_context": {"agentmap_hash": "agentmap_abc"},
        "proof_context": {
            "proof_hash": "proof_abc",
            "proof_receipt_id": "receipt_abc",
        },
        "ets_context": {"preview_only": True},
    }

    trace = build_reasoning_replay_trace(packet, snapshot)

    assert trace["evidence_context"]["source_reasoning_packet_hash"] == "reasoning_packet_abc"
    assert trace["evidence_context"]["reasoning_memory_snapshot_hash"] == "reasoning_memory_snapshot_abc"
    assert trace["evidence_context"]["agentmap_hash"] == "agentmap_abc"
    assert trace["evidence_context"]["proof_hash"] == "proof_abc"
    assert trace["evidence_context"]["proof_receipt_id"] == "receipt_abc"


def test_phase20c_is_deterministic_for_same_input():
    packet = {"reasoning_packet_hash": "rp_1", "website_intake": {"message": "Need repair"}}
    snapshot = {"snapshot_hash": "ms_1", "proof_context": {"proof_hash": "proof_1"}}

    first = build_reasoning_replay_trace(packet, snapshot)
    second = build_reasoning_replay_trace(packet, snapshot)

    assert first["replay_trace_hash"] == second["replay_trace_hash"]
    assert first["summary_hash"] == second["summary_hash"]


def test_phase20c_does_not_expose_private_chain_of_thought_or_secrets():
    packet = {
        "chain_of_thought": "ROOT_COT_VALUE",
        "private_chain_of_thought": "PRIVATE_COT_VALUE",
        "access_token": "ACCESS_TOKEN_VALUE",
        "api_key": "API_KEY_VALUE",
        "website_intake": {
            "message": "Need repair",
            "hidden_reasoning": "HIDDEN_VALUE",
        },
    }

    trace = build_reasoning_replay_trace(packet, {"snapshot_hash": "ms_1"})
    text = json.dumps(trace, sort_keys=True)

    assert "ROOT_COT_VALUE" not in text
    assert "PRIVATE_COT_VALUE" not in text
    assert "ACCESS_TOKEN_VALUE" not in text
    assert "API_KEY_VALUE" not in text
    assert "HIDDEN_VALUE" not in text

    assert trace["safety"]["private_reasoning_exposed"] is False
    assert trace["safety"]["credentials_retained"] is False


def test_phase20c_replay_trace_never_creates_side_effects():
    trace = build_default_home_fixed_reasoning_replay_trace()
    safety = trace["safety"]

    assert safety["would_create_booking"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_send_external_message"] is False
    assert safety["would_write_live_chain"] is False
    assert safety["would_execute_workflow"] is False
    assert safety["live_side_effects_enabled"] is False


def test_phase20c_replay_steps_are_visible_and_safe():
    trace = build_default_home_fixed_reasoning_replay_trace()

    assert len(trace["replay_steps"]) >= 5
    assert all(step["uses_private_reasoning"] is False for step in trace["replay_steps"])

    names = " ".join(step["name"] for step in trace["replay_steps"])
    assert "governed reasoning packet" in names
    assert "reasoning memory snapshot" in names
    assert "evidence and proof anchors" in names


def test_phase20c_summary_is_minimal_and_review_gated():
    trace = build_default_home_fixed_reasoning_replay_trace()
    summary = trace["summary"]

    assert summary["preview_only"] is True
    assert summary["human_review_required"] is True
    assert summary["private_reasoning_exposed"] is False
    assert summary["recommendation_state"] == "human_review_required"
    assert summary["replay_trace_hash"] == trace["replay_trace_hash"]
