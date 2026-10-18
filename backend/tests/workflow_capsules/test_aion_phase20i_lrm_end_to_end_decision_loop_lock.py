from backend.modules.aion_lrm.lrm_end_to_end_decision_loop import (
    LRM_END_TO_END_DECISION_LOOP_VERSION,
    build_default_home_fixed_lrm_end_to_end_decision_loop,
    build_lrm_end_to_end_decision_loop,
)


def test_phase20i_builds_end_to_end_loop():
    loop = build_default_home_fixed_lrm_end_to_end_decision_loop()

    assert loop["loop_version"] == LRM_END_TO_END_DECISION_LOOP_VERSION
    assert loop["loop_type"] == "aion_lrm_end_to_end_decision_loop"
    assert loop["business_id"] == "home_fixed"
    assert loop["loop_hash"].startswith("lrm_end_to_end_decision_loop_")
    assert loop["summary_hash"].startswith("lrm_end_to_end_decision_loop_summary_")


def test_phase20i_contains_all_lrm_chain_artifacts():
    loop = build_default_home_fixed_lrm_end_to_end_decision_loop()

    for key in [
        "governed_reasoning_packet",
        "reasoning_memory_snapshot",
        "reasoning_replay_trace",
        "boardroom_replay_panel",
        "reasoning_recommendation_card",
        "human_review_decision_envelope",
        "evidence_gap_envelope",
        "evidence_satisfaction_envelope",
    ]:
        assert key in loop


def test_phase20i_loop_steps_are_ordered():
    loop = build_default_home_fixed_lrm_end_to_end_decision_loop()
    names = [step["name"] for step in loop["loop_steps"]]

    assert names == [
        "governed_reasoning_packet",
        "reasoning_memory_snapshot",
        "reasoning_replay_trace",
        "boardroom_replay_visibility",
        "reasoning_recommendation_card",
        "human_review_decision_envelope",
        "evidence_gap_envelope",
        "evidence_satisfaction_envelope",
    ]


def test_phase20i_default_loop_returns_to_human_review():
    loop = build_default_home_fixed_lrm_end_to_end_decision_loop()

    assert loop["final_state"] == "return_to_human_review"
    assert loop["evidence_satisfaction_envelope"]["satisfaction_state"]["evidence_gap_satisfied"] is True


def test_phase20i_partial_evidence_keeps_more_evidence_state():
    loop = build_lrm_end_to_end_decision_loop(
        received_evidence={
            "site_photo": {
                "received": True,
                "evidence_hash": "site_photo_only",
            }
        }
    )

    assert loop["final_state"] == "request_more_evidence"
    assert loop["evidence_satisfaction_envelope"]["satisfaction_state"]["evidence_gap_satisfied"] is False


def test_phase20i_loop_links_all_hashes():
    loop = build_default_home_fixed_lrm_end_to_end_decision_loop()
    step_hashes = [step["hash"] for step in loop["loop_steps"]]

    assert all(step_hashes)
    assert loop["governed_reasoning_packet"]["reasoning_packet_hash"] in step_hashes
    assert loop["reasoning_memory_snapshot"]["snapshot_hash"] in step_hashes
    assert loop["reasoning_replay_trace"]["replay_trace_hash"] in step_hashes
    assert loop["reasoning_recommendation_card"]["card_hash"] in step_hashes


def test_phase20i_redacts_private_reasoning_and_credentials():
    loop = build_lrm_end_to_end_decision_loop(
        {
            "business_id": "home_fixed",
            "reasoning_packet_hash": "packet_hash",
            "private_chain_of_thought": "PRIVATE_COT_VALUE",
            "access_token": "ACCESS_TOKEN_VALUE",
            "api_key": "API_KEY_VALUE",
            "hidden_reasoning": "HIDDEN_REASONING_VALUE",
        }
    )

    text = str(loop)

    assert "PRIVATE_COT_VALUE" not in text
    assert "ACCESS_TOKEN_VALUE" not in text
    assert "API_KEY_VALUE" not in text
    assert "HIDDEN_REASONING_VALUE" not in text
    assert loop["safety"]["private_chain_of_thought_exposed"] is False
    assert loop["safety"]["hidden_reasoning_exposed"] is False
    assert loop["safety"]["credentials_exposed"] is False


def test_phase20i_blocks_all_live_side_effects():
    loop = build_default_home_fixed_lrm_end_to_end_decision_loop()
    safety = loop["safety"]

    assert safety["preview_only"] is True
    assert safety["human_review_required"] is True
    assert safety["end_to_end_loop_grants_live_permission"] is False
    assert safety["would_create_booking"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_send_external_message"] is False
    assert safety["would_write_live_chain"] is False
    assert safety["would_execute_workflow"] is False
    assert safety["live_side_effects_enabled"] is False


def test_phase20i_is_deterministic_for_same_inputs():
    one = build_default_home_fixed_lrm_end_to_end_decision_loop()
    two = build_default_home_fixed_lrm_end_to_end_decision_loop()

    assert one["loop_hash"] == two["loop_hash"]
    assert one["summary_hash"] == two["summary_hash"]
