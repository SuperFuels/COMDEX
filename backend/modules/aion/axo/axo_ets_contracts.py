from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


ETS_FEEDBACK_PACKET_VERSION = "aion.ets_feedback_packet.v0.1"


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
    evidence_ids = evidence_ids or ["evidence_preview"]

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

