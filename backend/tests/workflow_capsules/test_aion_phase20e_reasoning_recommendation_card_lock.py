from backend.modules.aion_lrm.reasoning_recommendation_card import (
    REASONING_RECOMMENDATION_CARD_VERSION,
    build_default_home_fixed_reasoning_recommendation_card,
    build_reasoning_recommendation_card,
)


def test_phase20e_builds_recommendation_card():
    card = build_default_home_fixed_reasoning_recommendation_card()

    assert card["card_version"] == REASONING_RECOMMENDATION_CARD_VERSION
    assert card["card_type"] == "boardroom_reasoning_recommendation"
    assert card["title"] == "AION Recommendation"
    assert card["business_id"] == "home_fixed"
    assert card["card_hash"].startswith("reasoning_recommendation_card_")
    assert card["summary_hash"].startswith("reasoning_recommendation_summary_")


def test_phase20e_recommendation_is_human_review_gated():
    card = build_default_home_fixed_reasoning_recommendation_card()

    assert card["recommendation"]["recommended_next_step"] == "human_review_required_before_live_action"
    assert card["recommendation"]["execution_status"] == "not_executed_preview_only"
    assert card["recommendation"]["operator_action"] == "review_before_approval"
    assert card["safety"]["recommendation_grants_permission"] is False
    assert card["safety"]["human_review_required"] is True


def test_phase20e_links_packet_memory_replay_and_boardroom_hashes():
    card = build_default_home_fixed_reasoning_recommendation_card()
    evidence = card["evidence_support"]

    assert evidence["reasoning_packet_hash"]
    assert evidence["memory_snapshot_hash"]
    assert evidence["replay_trace_hash"]
    assert evidence["boardroom_hash"]
    assert isinstance(evidence["evidence_hashes"], list)
    assert isinstance(evidence["proof_hashes"], list)
    assert isinstance(evidence["context_hashes"], list)


def test_phase20e_blocks_live_side_effects():
    card = build_default_home_fixed_reasoning_recommendation_card()
    safety = card["safety"]

    assert safety["preview_only"] is True
    assert safety["would_create_booking"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_send_external_message"] is False
    assert safety["would_write_live_chain"] is False
    assert safety["would_execute_workflow"] is False
    assert safety["live_side_effects_enabled"] is False


def test_phase20e_redacts_private_reasoning_and_credentials():
    card = build_reasoning_recommendation_card(
        reasoning_packet={
            "business_id": "home_fixed",
            "reasoning_packet_hash": "packet_hash",
            "private_chain_of_thought": "PRIVATE_COT_VALUE",
            "access_token": "ACCESS_TOKEN_VALUE",
        },
        memory_snapshot={
            "business_id": "home_fixed",
            "snapshot_hash": "memory_hash",
            "api_key": "API_KEY_VALUE",
        },
        replay_trace={
            "replay_trace_hash": "replay_hash",
            "hidden_reasoning": "HIDDEN_REASONING_VALUE",
            "governed_inputs": {
                "evidence_hashes": ["evidence_hash"],
                "proof_hashes": ["proof_hash"],
                "context_hashes": ["context_hash"],
            },
        },
    )

    text = str(card)

    assert "PRIVATE_COT_VALUE" not in text
    assert "ACCESS_TOKEN_VALUE" not in text
    assert "API_KEY_VALUE" not in text
    assert "HIDDEN_REASONING_VALUE" not in text
    assert card["safety"]["private_chain_of_thought_exposed"] is False
    assert card["safety"]["hidden_reasoning_exposed"] is False
    assert card["safety"]["credentials_exposed"] is False


def test_phase20e_is_deterministic_for_same_inputs():
    one = build_default_home_fixed_reasoning_recommendation_card()
    two = build_default_home_fixed_reasoning_recommendation_card()

    assert one["card_hash"] == two["card_hash"]
    assert one["summary_hash"] == two["summary_hash"]


def test_phase20e_custom_recommendation_label_is_supported():
    card = build_reasoning_recommendation_card(
        recommendation_label="Request more evidence before approval",
        confidence="low",
    )

    assert card["recommendation"]["recommendation_label"] == "Request more evidence before approval"
    assert card["recommendation"]["confidence"] == "low"
    assert card["summary"]["confidence"] == "low"
