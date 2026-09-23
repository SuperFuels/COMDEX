from backend.modules.aion.axo.axo_ets_contracts import (
    AXO_ANTI_GAMING_RULES,
    AXO_ANTI_GAMING_RULESET_VERSION,
    AXO_TRUST_RULE_LOCK_VERSION,
    build_axo_anti_gaming_agentmap_extension,
    build_axo_trust_rule_lock_preview,
    build_ets_feedback_packet_preview,
)


def test_phase15d_defines_anti_gaming_ruleset():
    assert AXO_ANTI_GAMING_RULES["version"] == AXO_ANTI_GAMING_RULESET_VERSION
    assert AXO_ANTI_GAMING_RULES["preview_only"] is True
    assert AXO_ANTI_GAMING_RULES["live_reputation_mutation_allowed"] is False

    rules = AXO_ANTI_GAMING_RULES["rules"]
    for key in [
        "signed_feedback_required",
        "proof_receipt_required",
        "evidence_required",
        "job_trace_required",
        "customer_system_score_separation_required",
        "self_scoring_blocked",
        "human_review_required_for_trust_mutation",
    ]:
        assert key in rules
        assert rules[key]["required"] is True


def test_phase15d_trust_rule_lock_is_preview_only():
    lock = build_axo_trust_rule_lock_preview()

    assert lock["lock_version"] == AXO_TRUST_RULE_LOCK_VERSION
    assert lock["ruleset_version"] == AXO_ANTI_GAMING_RULESET_VERSION
    assert lock["preview_only"] is True
    assert lock["anti_gaming_locked"] is True
    assert lock["trust_rules_locked"] is True
    assert lock["trusted_score_allowed"] is False
    assert lock["live_reputation_mutation_allowed"] is False
    assert lock["human_review_required"] is True


def test_phase15d_signature_not_verified_blocks_trust():
    packet = build_ets_feedback_packet_preview(signature_preview="signed-preview")
    lock = build_axo_trust_rule_lock_preview(packet)

    assert lock["checks"]["signed_feedback_present"] is True
    assert lock["checks"]["signature_verified"] is False
    assert "signature_not_verified" in lock["blocking_reasons"]
    assert lock["trusted_score_allowed"] is False


def test_phase15d_requires_proof_evidence_and_trace_links():
    packet = build_ets_feedback_packet_preview(
        proof_receipt_id="",
        job_trace_id="",
        evidence_ids=[],
    )
    lock = build_axo_trust_rule_lock_preview(packet)

    assert "proof_receipt_required" in lock["blocking_reasons"]
    assert "job_trace_required" in lock["blocking_reasons"]
    assert "evidence_required" in lock["blocking_reasons"]


def test_phase15d_customer_and_system_scores_must_remain_separate():
    packet = build_ets_feedback_packet_preview()
    packet["score_separation"]["must_not_merge_customer_and_system_scores"] = False

    lock = build_axo_trust_rule_lock_preview(packet)

    assert lock["checks"]["customer_system_scores_separated"] is False
    assert "customer_system_score_separation_required" in lock["blocking_reasons"]


def test_phase15d_agentmap_extension_exposes_lock_state():
    extension = build_axo_anti_gaming_agentmap_extension()

    assert extension["agentmap_extension"] == "aion.axo_anti_gaming_preview.v0.1"
    assert extension["preview_only"] is True
    assert extension["anti_gaming_locked"] is True
    assert extension["trust_rules_locked"] is True
    assert extension["trusted_score_allowed"] is False
    assert extension["human_review_required"] is True
    assert "blocking_reasons" in extension
    assert "checks" in extension


def test_phase15d_no_live_side_effects_enabled():
    lock = build_axo_trust_rule_lock_preview()

    safety = lock["safety"]
    assert safety["no_live_reputation_write"] is True
    assert safety["no_autonomous_score_acceptance"] is True
    assert safety["no_customer_system_score_merge"] is True
    assert safety["no_booking_side_effect"] is True
    assert safety["no_payment_side_effect"] is True
    assert safety["no_escrow_side_effect"] is True
