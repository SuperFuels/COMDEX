from backend.modules.aion.axo.axo_ets_contracts import (
    AXO_SCORING_VOCABULARY,
    ETS_FEEDBACK_PACKET_VERSION,
    build_ets_agentmap_preview,
    build_ets_feedback_packet_preview,
    validate_ets_feedback_packet_preview,
)


def test_phase15a_defines_axo_scoring_vocabulary():
    vocab = AXO_SCORING_VOCABULARY

    assert vocab["version"] == "aion.axo_scoring_vocabulary.v0.1"
    assert vocab["score_scale"]["min"] == 0
    assert vocab["score_scale"]["max"] == 100

    for key in [
        "customer_outcome_score",
        "system_execution_score",
        "agent_reliability_score",
        "evidence_quality_score",
        "trust_readiness_score",
    ]:
        assert key in vocab["score_classes"]


def test_phase15a_ets_feedback_packet_schema_is_preview_only():
    packet = build_ets_feedback_packet_preview()

    assert packet["packet_version"] == ETS_FEEDBACK_PACKET_VERSION
    assert packet["preview_only"] is True
    assert packet["anti_gaming_locked"] is False
    assert packet["live_reputation_mutation_allowed"] is False
    assert packet["human_review_required"] is True
    assert packet["ets_feedback_hash"]


def test_phase15a_accepts_signed_external_agent_feedback_preview_only():
    packet = build_ets_feedback_packet_preview(
        external_agent_id="agent_test_external",
        signature_preview="sig_test_preview",
    )

    assert packet["external_agent"]["agent_id"] == "agent_test_external"
    assert packet["external_agent"]["signature_preview"] == "sig_test_preview"
    assert packet["external_agent"]["signed_external_agent_feedback_preview"] is True
    assert packet["external_agent"]["signature_verified"] is False


def test_phase15a_customer_outcome_score_is_separate_from_system_execution_score():
    packet = build_ets_feedback_packet_preview(
        customer_outcome_score=82,
        system_execution_score=64,
    )

    assert packet["scores"]["customer_outcome_score"] == 82
    assert packet["scores"]["system_execution_score"] == 64
    assert packet["scores"]["customer_outcome_score"] != packet["scores"]["system_execution_score"]
    assert packet["score_separation"]["must_not_merge_customer_and_system_scores"] is True


def test_phase15a_links_ets_to_proof_receipts_evidence_and_job_trace():
    packet = build_ets_feedback_packet_preview(
        job_trace_id="job_trace_home_fixed_001",
        proof_receipt_id="proof_receipt_001",
        evidence_ids=["evidence_quote_001", "evidence_completion_001"],
    )

    links = packet["trace_links"]
    assert links["job_trace_id"] == "job_trace_home_fixed_001"
    assert links["proof_receipt_id"] == "proof_receipt_001"
    assert links["evidence_ids"] == ["evidence_quote_001", "evidence_completion_001"]


def test_phase15a_validates_packet_and_blocks_live_side_effects():
    packet = build_ets_feedback_packet_preview()
    validation = validate_ets_feedback_packet_preview(packet)

    assert validation["ok"] is True
    assert validation["status"] == "valid_preview"

    safety = packet["safety"]
    assert safety["preview_only"] is True
    assert safety["no_live_reputation_write"] is True
    assert safety["no_autonomous_score_acceptance"] is True
    assert safety["no_booking_side_effect"] is True
    assert safety["no_payment_side_effect"] is True
    assert safety["no_escrow_side_effect"] is True


def test_phase15a_exposes_ets_preview_for_agentmap_extension():
    packet = build_ets_feedback_packet_preview()
    agentmap_preview = build_ets_agentmap_preview(packet)

    assert agentmap_preview["agentmap_extension"] == "aion.ets_preview.v0.1"
    assert agentmap_preview["preview_only"] is True
    assert agentmap_preview["anti_gaming_locked"] is False
    assert agentmap_preview["trust_rules_locked"] is False

    ets = agentmap_preview["execution_trust_score_preview"]
    assert ets["ets_feedback_hash"] == packet["ets_feedback_hash"]
    assert ets["trace_links"]["proof_receipt_id"]
    assert ets["score_separation"]["must_not_merge_customer_and_system_scores"] is True
    assert ets["live_reputation_mutation_allowed"] is False
