from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


ETS_FEEDBACK_PACKET_VERSION = "aion.ets_feedback_packet.v0.1"
TRUSTED_FEEDBACK_ACCEPTANCE_VERSION = "aion.trusted_feedback_acceptance.v0.1"


AXO_SCORING_VOCABULARY: dict[str, Any] = {
    "version": "aion.axo_scoring_vocabulary.v0.1",
    "score_scale": {
        "min": 0,
        "max": 100,
        "meaning": "Higher is better. Scores are preview-only until anti-gaming rules are locked.",
    },
    "score_classes": {
        "customer_outcome_score": {
            "description": "Customer-visible outcome satisfaction and service quality signal.",
            "must_not_replace": "system_execution_score",
        },
        "system_execution_score": {
            "description": "Machine execution quality, evidence completeness, policy compliance, and trace integrity.",
            "must_not_replace": "customer_outcome_score",
        },
        "agent_reliability_score": {
            "description": "External or internal agent reliability preview based on signed feedback and evidence-linked traces.",
        },
        "evidence_quality_score": {
            "description": "Strength, completeness, and verifiability of evidence attached to a job trace.",
        },
        "trust_readiness_score": {
            "description": "Composite preview signal showing whether the business twin is ready for more trusted automation.",
        },
    },
    "required_boundaries": {
        "preview_only": True,
        "anti_gaming_locked": False,
        "live_reputation_mutation_allowed": False,
        "customer_outcome_separate_from_system_execution": True,
        "human_review_required_for_trust_changes": True,
    },
}


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_ets_feedback_packet_preview(
    *,
    external_agent_id: str = "external_agent_preview",
    business_id: str = "home_fixed",
    job_trace_id: str = "job_trace_preview",
    proof_receipt_id: str = "proof_receipt_preview",
    evidence_ids: list[str] | None = None,
    customer_outcome_score: int = 0,
    system_execution_score: int = 0,
    agent_reliability_score: int = 0,
    evidence_quality_score: int = 0,
    signature_preview: str = "signature_preview_unverified",
) -> dict[str, Any]:
    if evidence_ids is None:
        evidence_ids = ["evidence_preview"]

    packet: dict[str, Any] = {
        "packet_version": ETS_FEEDBACK_PACKET_VERSION,
        "created_at": _now_iso(),
        "preview_only": True,
        "anti_gaming_locked": False,
        "live_reputation_mutation_allowed": False,
        "human_review_required": True,
        "external_agent": {
            "agent_id": external_agent_id,
            "signature_preview": signature_preview,
            "signature_verified": False,
            "signed_external_agent_feedback_preview": True,
        },
        "business_id": business_id,
        "trace_links": {
            "job_trace_id": job_trace_id,
            "proof_receipt_id": proof_receipt_id,
            "evidence_ids": evidence_ids,
        },
        "scores": {
            "customer_outcome_score": customer_outcome_score,
            "system_execution_score": system_execution_score,
            "agent_reliability_score": agent_reliability_score,
            "evidence_quality_score": evidence_quality_score,
        },
        "score_separation": {
            "customer_outcome_score_is_customer_signal": True,
            "system_execution_score_is_machine_execution_signal": True,
            "must_not_merge_customer_and_system_scores": True,
        },
        "safety": {
            "preview_only": True,
            "no_live_reputation_write": True,
            "no_autonomous_score_acceptance": True,
            "no_booking_side_effect": True,
            "no_payment_side_effect": True,
            "no_escrow_side_effect": True,
            "human_review_required": True,
        },
    }

    packet["ets_feedback_hash"] = _sha256(
        {
            "packet_version": packet["packet_version"],
            "external_agent": packet["external_agent"],
            "business_id": packet["business_id"],
            "trace_links": packet["trace_links"],
            "scores": packet["scores"],
            "score_separation": packet["score_separation"],
            "safety": packet["safety"],
        }
    )

    return packet


def validate_ets_feedback_packet_preview(packet: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    if packet.get("packet_version") != ETS_FEEDBACK_PACKET_VERSION:
        errors.append("invalid_packet_version")

    if packet.get("preview_only") is not True:
        errors.append("preview_only_required")

    if packet.get("live_reputation_mutation_allowed") is not False:
        errors.append("live_reputation_mutation_must_be_false")

    scores = packet.get("scores") or {}
    for key in [
        "customer_outcome_score",
        "system_execution_score",
        "agent_reliability_score",
        "evidence_quality_score",
    ]:
        value = scores.get(key)
        if not isinstance(value, int) or value < 0 or value > 100:
            errors.append(f"invalid_score:{key}")

    separation = packet.get("score_separation") or {}
    if separation.get("must_not_merge_customer_and_system_scores") is not True:
        errors.append("customer_and_system_scores_must_be_separate")

    trace_links = packet.get("trace_links") or {}
    if not trace_links.get("proof_receipt_id"):
        errors.append("proof_receipt_link_required")
    if not trace_links.get("job_trace_id"):
        errors.append("job_trace_link_required")
    if not trace_links.get("evidence_ids"):
        errors.append("evidence_link_required")

    safety = packet.get("safety") or {}
    for key in [
        "preview_only",
        "no_live_reputation_write",
        "no_autonomous_score_acceptance",
        "no_booking_side_effect",
        "no_payment_side_effect",
        "no_escrow_side_effect",
        "human_review_required",
    ]:
        if safety.get(key) is not True:
            errors.append(f"safety_required:{key}")

    return {
        "ok": not errors,
        "status": "valid_preview" if not errors else "invalid_preview",
        "errors": errors,
        "preview_only": True,
    }


def build_ets_agentmap_preview(packet: dict[str, Any] | None = None) -> dict[str, Any]:
    packet = packet or build_ets_feedback_packet_preview()

    return {
        "agentmap_extension": "aion.ets_preview.v0.1",
        "preview_only": True,
        "anti_gaming_locked": False,
        "trust_rules_locked": False,
        "execution_trust_score_preview": {
            "ets_feedback_hash": packet.get("ets_feedback_hash"),
            "business_id": packet.get("business_id"),
            "trace_links": packet.get("trace_links"),
            "scores": packet.get("scores"),
            "score_separation": packet.get("score_separation"),
            "human_review_required": True,
            "live_reputation_mutation_allowed": False,
        },
    }


def attach_ets_preview_to_agentmap(
    agentmap: dict[str, Any],
    packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Attach the preview-only ETS projection to an AgentMap payload.

    This is a visibility/export contract only. It MUST NOT mutate reputation,
    publish rankings, accept quotes, create bookings, move money, create escrow,
    send external messages, or bypass human review.
    """
    source = dict(agentmap or {})
    ets_preview = build_ets_agentmap_preview(packet)

    ets_preview["preview_only"] = True
    ets_preview["anti_gaming_locked"] = False
    ets_preview["trust_rules_locked"] = False
    ets_preview["human_review_required"] = True
    ets_preview["live_reputation_mutation_enabled"] = False
    ets_preview["public_ranking_enabled"] = False

    proof_links = (
        ets_preview
        .get("execution_trust_score_preview", {})
        .get("trace_links", {})
    )

    ets_preview["proof_links"] = {
        "job_trace_id": proof_links.get("job_trace_id") or "job_trace_preview",
        "proof_receipt_id": proof_links.get("proof_receipt_id") or "proof_receipt_preview",
        "evidence_ids": proof_links.get("evidence_ids") or ["evidence_preview"],
    }

    source["ets_preview"] = ets_preview

    capabilities = dict(source.get("capabilities") or {})
    capabilities["ets_preview"] = {
        "available": True,
        "preview_only": True,
        "human_review_required": True,
        "live_reputation_mutation_enabled": False,
        "public_ranking_enabled": False,
    }
    source["capabilities"] = capabilities

    return source

def build_axo_readiness_dashboard_preview(
    packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a preview-only AXO readiness dashboard payload.

    This is a Boardroom/read-only summary. It must not mutate reputation,
    rankings, proof receipts, jobs, payments, bookings, escrow, or external
    channels.
    """
    packet = packet or build_ets_feedback_packet_preview()
    validation = validate_ets_feedback_packet_preview(packet)
    ets_preview = build_ets_agentmap_preview(packet)
    scores = packet.get("scores") or {}
    trace_links = packet.get("trace_links") or {}
    external_agent = packet.get("external_agent") or {}

    customer_score = scores.get("customer_outcome_score", 0)
    system_score = scores.get("system_execution_score", 0)
    evidence_score = scores.get("evidence_quality_score", 0)
    agent_score = scores.get("agent_reliability_score", 0)

    readiness_inputs = [
        int(customer_score or 0),
        int(system_score or 0),
        int(evidence_score or 0),
        int(agent_score or 0),
    ]
    readiness_score = int(sum(readiness_inputs) / len(readiness_inputs)) if readiness_inputs else 0

    blockers: list[str] = []
    if validation.get("ok") is not True:
        blockers.extend(validation.get("errors") or [])
    if external_agent.get("signature_verified") is not True:
        blockers.append("external_agent_signature_not_verified")
    if ets_preview.get("anti_gaming_locked") is not True:
        blockers.append("anti_gaming_rules_not_locked")
    if ets_preview.get("trust_rules_locked") is not True:
        blockers.append("trust_rules_not_locked")

    return {
        "dashboard_version": "aion.axo_readiness_dashboard.v0.1",
        "status": "preview_ready",
        "preview_only": True,
        "business_id": packet.get("business_id"),
        "readiness_score_preview": readiness_score,
        "readiness_state": "blocked_preview" if blockers else "ready_preview",
        "score_classes": {
            "customer_outcome_score": customer_score,
            "system_execution_score": system_score,
            "agent_reliability_score": agent_score,
            "evidence_quality_score": evidence_score,
        },
        "score_separation": {
            "customer_outcome_score_is_customer_signal": True,
            "system_execution_score_is_machine_execution_signal": True,
            "must_not_merge_customer_and_system_scores": True,
        },
        "trust_controls": {
            "anti_gaming_locked": False,
            "trust_rules_locked": False,
            "human_review_required": True,
            "live_reputation_mutation_allowed": False,
            "public_ranking_enabled": False,
        },
        "trace_links": {
            "job_trace_id": trace_links.get("job_trace_id"),
            "proof_receipt_id": trace_links.get("proof_receipt_id"),
            "evidence_ids": trace_links.get("evidence_ids") or [],
            "ets_feedback_hash": packet.get("ets_feedback_hash"),
        },
        "blockers": blockers,
        "safety": {
            "preview_only": True,
            "read_only": True,
            "no_live_reputation_write": True,
            "no_public_ranking_write": True,
            "no_autonomous_score_acceptance": True,
            "no_booking_side_effect": True,
            "no_payment_side_effect": True,
            "no_escrow_side_effect": True,
            "no_external_message_side_effect": True,
            "human_review_required": True,
        },
    }


# ---------------------------------------------------------------------------
# Phase 15D — Anti-gaming + Trust Rule Lock Foundation
# ---------------------------------------------------------------------------

AXO_ANTI_GAMING_RULESET_VERSION = "aion.axo_anti_gaming_ruleset.v0.1"
AXO_TRUST_RULE_LOCK_VERSION = "aion.axo_trust_rule_lock.v0.1"
AXO_HUMAN_REVIEW_DECISION_PREVIEW_VERSION = "aion.axo_human_review_decision_preview.v0.1"


AXO_ANTI_GAMING_RULES: dict[str, Any] = {
    "version": AXO_ANTI_GAMING_RULESET_VERSION,
    "preview_only": True,
    "rules": {
        "signed_feedback_required": {
            "description": "External-agent feedback must be signed before it can contribute to trusted scoring.",
            "required": True,
        },
        "proof_receipt_required": {
            "description": "ETS feedback must link to a verifiable proof receipt.",
            "required": True,
        },
        "evidence_required": {
            "description": "ETS feedback must link to at least one evidence item.",
            "required": True,
        },
        "job_trace_required": {
            "description": "ETS feedback must link to the job trace being scored.",
            "required": True,
        },
        "customer_system_score_separation_required": {
            "description": "Customer outcome score and system execution score must remain separate.",
            "required": True,
        },
        "self_scoring_blocked": {
            "description": "A business or agent must not directly approve its own trust mutation.",
            "required": True,
        },
        "human_review_required_for_trust_mutation": {
            "description": "Any future trust/reputation mutation requires human review.",
            "required": True,
        },
    },
    "live_reputation_mutation_allowed": False,
}


def build_axo_trust_rule_lock_preview(
    packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    packet = packet or build_ets_feedback_packet_preview()
    validation = validate_ets_feedback_packet_preview(packet)

    trace_links = packet.get("trace_links") or {}
    external_agent = packet.get("external_agent") or {}
    score_separation = packet.get("score_separation") or {}

    checks = {
        "signed_feedback_present": bool(external_agent.get("signature_preview")),
        "signature_verified": external_agent.get("signature_verified") is True,
        "proof_receipt_linked": bool(trace_links.get("proof_receipt_id")),
        "job_trace_linked": bool(trace_links.get("job_trace_id")),
        "evidence_linked": bool(trace_links.get("evidence_ids")),
        "customer_system_scores_separated": (
            score_separation.get("must_not_merge_customer_and_system_scores") is True
        ),
        "packet_valid_preview": validation.get("ok") is True,
        "human_review_required": packet.get("human_review_required") is True,
        "live_reputation_mutation_allowed": packet.get("live_reputation_mutation_allowed") is True,
    }

    blocking_reasons: list[str] = []

    if not checks["signed_feedback_present"]:
        blocking_reasons.append("signed_feedback_required")
    if not checks["signature_verified"]:
        blocking_reasons.append("signature_not_verified")
    if not checks["proof_receipt_linked"]:
        blocking_reasons.append("proof_receipt_required")
    if not checks["job_trace_linked"]:
        blocking_reasons.append("job_trace_required")
    if not checks["evidence_linked"]:
        blocking_reasons.append("evidence_required")
    if not checks["customer_system_scores_separated"]:
        blocking_reasons.append("customer_system_score_separation_required")
    if checks["live_reputation_mutation_allowed"]:
        blocking_reasons.append("live_reputation_mutation_forbidden_in_preview")

    trusted_score_allowed = False

    return {
        "lock_version": AXO_TRUST_RULE_LOCK_VERSION,
        "ruleset_version": AXO_ANTI_GAMING_RULESET_VERSION,
        "preview_only": True,
        "anti_gaming_locked": True,
        "trust_rules_locked": True,
        "trusted_score_allowed": trusted_score_allowed,
        "human_review_required": True,
        "live_reputation_mutation_allowed": False,
        "checks": checks,
        "blocking_reasons": blocking_reasons,
        "status": "blocked_preview" if blocking_reasons else "review_required_preview",
        "safety": {
            "no_live_reputation_write": True,
            "no_autonomous_score_acceptance": True,
            "no_customer_system_score_merge": True,
            "no_booking_side_effect": True,
            "no_payment_side_effect": True,
            "no_escrow_side_effect": True,
        },
    }


def build_axo_anti_gaming_agentmap_extension(
    packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lock = build_axo_trust_rule_lock_preview(packet)

    return {
        "agentmap_extension": "aion.axo_anti_gaming_preview.v0.1",
        "preview_only": True,
        "anti_gaming_locked": lock["anti_gaming_locked"],
        "trust_rules_locked": lock["trust_rules_locked"],
        "trusted_score_allowed": lock["trusted_score_allowed"],
        "human_review_required": lock["human_review_required"],
        "blocking_reasons": lock["blocking_reasons"],
        "checks": lock["checks"],
        "safety": lock["safety"],
    }


def build_trusted_feedback_acceptance_preview(
    packet: dict[str, Any] | None = None,
    *,
    operator_decision: str = "pending_human_review",
) -> dict[str, Any]:
    """Build a guarded trusted-feedback acceptance preview.

    This preview can mark a signed/external feedback packet as eligible for
    human review, rejected for explicit lock reasons, or still pending. It
    never mutates reputation, trust scores, booking state, payment state, or
    public trust state.
    """
    packet = packet or build_ets_feedback_packet_preview()
    validation = validate_ets_feedback_packet_preview(packet)

    trust_rule = build_axo_trust_rule_lock_preview(packet)
    blocking_reasons = list(trust_rule.get("blocking_reasons") or [])

    external_agent = packet.get("external_agent") or {}
    signature_verified = external_agent.get("signature_verified") is True

    allowed_decisions = {
        "pending_human_review",
        "eligible_for_human_review",
        "rejected_preview",
    }

    if operator_decision not in allowed_decisions:
        operator_decision = "pending_human_review"
        blocking_reasons.append("invalid_operator_decision_normalised")

    eligible_for_human_review = (
        validation.get("ok") is True
        and signature_verified is True
        and not blocking_reasons
    )

    if operator_decision == "eligible_for_human_review" and not eligible_for_human_review:
        operator_decision = "rejected_preview"
        if "not_eligible_for_human_review" not in blocking_reasons:
            blocking_reasons.append("not_eligible_for_human_review")

    if operator_decision == "eligible_for_human_review":
        acceptance_status = "eligible_for_human_review"
    elif operator_decision == "rejected_preview":
        acceptance_status = "rejected_preview"
    elif eligible_for_human_review:
        acceptance_status = "ready_for_human_review"
    else:
        acceptance_status = "blocked_pending_review"

    preview = {
        "acceptance_version": TRUSTED_FEEDBACK_ACCEPTANCE_VERSION,
        "preview_only": True,
        "acceptance_status": acceptance_status,
        "operator_decision": operator_decision,
        "eligible_for_human_review": eligible_for_human_review,
        "human_review_required": True,
        "packet_validation": validation,
        "trust_rule_preview": trust_rule,
        "blocking_reasons": blocking_reasons,
        "accepted_packet": {
            "ets_feedback_hash": packet.get("ets_feedback_hash"),
            "business_id": packet.get("business_id"),
            "external_agent_id": external_agent.get("agent_id"),
            "signature_verified": signature_verified,
            "trace_links": packet.get("trace_links"),
            "scores": packet.get("scores"),
            "score_separation": packet.get("score_separation"),
        },
        "side_effects": {
            "reputation_mutation": False,
            "trust_score_mutation": False,
            "public_trust_state_mutation": False,
            "booking_created": False,
            "payment_created": False,
            "escrow_created": False,
            "external_message_sent": False,
        },
        "safety": {
            "preview_only": True,
            "no_live_reputation_write": True,
            "no_live_trust_score_write": True,
            "no_public_trust_state_write": True,
            "no_autonomous_acceptance": True,
            "no_booking_side_effect": True,
            "no_payment_side_effect": True,
            "no_escrow_side_effect": True,
            "human_review_required": True,
        },
    }

    preview["trusted_feedback_acceptance_hash"] = _sha256(
        {
            "acceptance_version": preview["acceptance_version"],
            "acceptance_status": preview["acceptance_status"],
            "operator_decision": preview["operator_decision"],
            "eligible_for_human_review": preview["eligible_for_human_review"],
            "accepted_packet": preview["accepted_packet"],
            "side_effects": preview["side_effects"],
            "safety": preview["safety"],
            "blocking_reasons": preview["blocking_reasons"],
        }
    )

    return preview

def build_axo_human_review_decision_preview(
    packet: dict[str, Any] | None = None,
    *,
    requested_decision: str = "request_more_evidence",
) -> dict[str, Any]:
    """Build a preview-only human-review decision envelope for AXO/ETS feedback.

    This function intentionally does not mutate reputation, public trust state,
    booking state, payment state, escrow state, external messaging, or live
    execution state.
    """

    allowed_decisions = {"accept", "reject", "request_more_evidence"}
    if requested_decision not in allowed_decisions:
        requested_decision = "request_more_evidence"

    packet = packet or build_ets_feedback_packet_preview()
    acceptance = build_trusted_feedback_acceptance_preview(packet)

    eligible_for_human_review = bool(
        acceptance.get("eligible_for_human_review")
        or acceptance.get("eligible")
        or acceptance.get("review_gate", {}).get("eligible_for_human_review")
    )

    blocking_reasons = list(
        acceptance.get("blocking_reasons")
        or acceptance.get("blockers")
        or acceptance.get("review_gate", {}).get("blocking_reasons")
        or []
    )

    if not eligible_for_human_review and "not_eligible_for_human_review" not in blocking_reasons:
        blocking_reasons.append("not_eligible_for_human_review")

    score_separation = packet.get("score_separation") or {
        "customer_outcome_score_is_customer_signal": True,
        "system_execution_score_is_machine_execution_signal": True,
        "must_not_merge_customer_and_system_scores": True,
    }

    side_effect_guards = {
        "reputation_mutation_allowed": False,
        "public_trust_update_allowed": False,
        "booking_side_effect_allowed": False,
        "payment_side_effect_allowed": False,
        "escrow_side_effect_allowed": False,
        "external_message_side_effect_allowed": False,
        "live_execution_allowed": False,
    }

    return {
        "decision_preview_version": "aion.axo_human_review_decision_preview.v0.1",
        "preview_only": True,
        "human_review_required": True,
        "automated_decision_allowed": False,
        "requested_decision": requested_decision,
        "decision": requested_decision,
        "allowed_decisions": sorted(allowed_decisions),
        "eligible_for_human_review": eligible_for_human_review,
        "blocking_reasons": blocking_reasons,
        "packet": {
            **packet,
            "score_separation": score_separation,
        },
        "trusted_feedback_acceptance_preview": acceptance,
        "score_separation": score_separation,
        "side_effect_guards": side_effect_guards,
        "safety": {
            "preview_only": True,
            "human_review_required": True,
            "automated_decision_allowed": False,
            "no_reputation_mutation": True,
            "no_public_trust_update": True,
            "no_booking_side_effect": True,
            "no_payment_side_effect": True,
            "no_escrow_side_effect": True,
            "no_external_message_side_effect": True,
            "no_live_execution": True,
        },
    }


