from backend.modules.aion_lrm.reasoning_replay_boardroom import (
    REASONING_REPLAY_BOARDROOM_VERSION,
    build_default_home_fixed_reasoning_replay_boardroom_panel,
    build_reasoning_replay_boardroom_panel,
)


def test_phase20d_builds_boardroom_reasoning_replay_panel():
    panel = build_default_home_fixed_reasoning_replay_boardroom_panel()

    assert panel["boardroom_panel_version"] == REASONING_REPLAY_BOARDROOM_VERSION
    assert panel["panel_title"] == "Reasoning Replay Trace"
    assert panel["panel_status"] == "preview_only"
    assert panel["summary"]["preview_only"] is True
    assert panel["summary"]["human_review_required"] is True
    assert panel["boardroom_hash"].startswith("reasoning_replay_boardroom_")
    assert panel["summary_hash"].startswith("reasoning_replay_boardroom_summary_")


def test_phase20d_exposes_governed_replay_inputs_not_private_reasoning():
    panel = build_default_home_fixed_reasoning_replay_boardroom_panel()
    summary = panel["reasoning_summary"]

    assert "reasoning_packet_hash" in summary
    assert "memory_snapshot_hash" in summary
    assert "replay_trace_hash" in summary
    assert "evidence_hashes" in summary
    assert "proof_hashes" in summary
    assert "context_hashes" in summary

    text = str(panel)
    assert "access_token" not in text
    assert "api_key" not in text
    assert "password" not in text

    # Safety/policy keys are allowed because they prove the exposure boundary.
    assert panel["safety"]["private_chain_of_thought_exposed"] is False
    assert panel["safety"]["hidden_reasoning_exposed"] is False
    assert panel["safety"]["credentials_exposed"] is False


def test_phase20d_redacts_private_fields_from_custom_trace():
    panel = build_reasoning_replay_boardroom_panel({
        "recommendation": "request_human_review",
        "decision_basis": ["Matched website intake to commercial ticket"],
        "reasoning_packet_hash": "reasoning_packet_test",
        "memory_snapshot_hash": "memory_snapshot_test",
        "replay_trace_hash": "replay_trace_test",
        "evidence_hashes": ["evidence_hash_test"],
        "proof_hashes": ["proof_hash_test"],
        "context_hashes": {"agentmap_context": "agentmap_hash_test"},
        "private_chain_of_thought": "PRIVATE_COT_VALUE",
        "hidden_reasoning": "HIDDEN_REASONING_VALUE",
        "access_token": "ACCESS_TOKEN_VALUE",
    })

    text = str(panel)

    assert "PRIVATE_COT_VALUE" not in text
    assert "HIDDEN_REASONING_VALUE" not in text
    assert "ACCESS_TOKEN_VALUE" not in text
    assert "access_token" not in text

    # Safety/policy keys are allowed because they prove the exposure boundary.
    assert panel["safety"]["private_chain_of_thought_exposed"] is False
    assert panel["safety"]["hidden_reasoning_exposed"] is False
    assert panel["safety"]["credentials_exposed"] is False


def test_phase20d_side_effects_are_blocked():
    panel = build_default_home_fixed_reasoning_replay_boardroom_panel()
    safety = panel["safety"]

    assert safety["preview_only"] is True
    assert safety["human_review_required"] is True
    assert safety["private_chain_of_thought_exposed"] is False
    assert safety["hidden_reasoning_exposed"] is False
    assert safety["credentials_exposed"] is False
    assert safety["would_create_booking"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_send_external_message"] is False
    assert safety["would_write_live_chain"] is False
    assert safety["would_execute_workflow"] is False
    assert safety["live_side_effects_enabled"] is False


def test_phase20d_hash_is_deterministic():
    one = build_default_home_fixed_reasoning_replay_boardroom_panel()
    two = build_default_home_fixed_reasoning_replay_boardroom_panel()

    assert one["boardroom_hash"] == two["boardroom_hash"]
    assert one["summary_hash"] == two["summary_hash"]
