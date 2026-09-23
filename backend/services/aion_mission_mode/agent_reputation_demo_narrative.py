from __future__ import annotations

from hashlib import sha256
import json
from typing import Any


LIVE_REPUTATION_MUTATION_FIELDS = {
    "commit_ets",
    "write_live_reputation",
    "mutate_agent_score",
    "publish_trust_score",
    "update_public_reputation",
    "promote_preview_to_live",
}

REQUIRED_DEMO_MESSAGE = "AION stopped itself before doing anything risky"

VALID_REPUTATION_STATES = {
    "ets_preview_only",
    "live_reputation_blocked",
    "governance_required",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def assert_reputation_preview_only(payload: dict[str, Any]) -> dict[str, Any]:
    violations: list[str] = []

    for field in LIVE_REPUTATION_MUTATION_FIELDS:
        if payload.get(field):
            violations.append(f"live_reputation_mutation_blocked:{field}")

    if payload.get("ets_state") not in {None, "preview_only"}:
        violations.append("ets_state_must_remain_preview_only")

    allowed = not violations

    result = {
        "schema_version": "aion.reputation_preview_guard.v0",
        "allowed": allowed,
        "reputation_state": "ets_preview_only" if allowed else "live_reputation_blocked",
        "violations": violations,
        "guard_hash": "",
    }
    result["guard_hash"] = _hash({k: v for k, v in result.items() if k != "guard_hash"})
    return result


def create_demo_narrative(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    outcome_packet_hash: str,
    ets_preview_hash: str,
    autonomy_percentage: float,
    checkpoint_count: int,
    blocked_action_count: int,
    receipt_count: int,
    estimated_minutes_saved: float,
) -> dict[str, Any]:
    for name, value in {
        "outcome_packet_hash": outcome_packet_hash,
        "ets_preview_hash": ets_preview_hash,
    }.items():
        if not isinstance(value, str) or not value.startswith("sha256:"):
            raise ValueError(f"{name} must be sha256-prefixed")

    narrative = {
        "schema_version": "aion.demo_narrative.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "headline": "AION completed safe work autonomously and stopped before risky actions.",
        "required_visible_message": REQUIRED_DEMO_MESSAGE,
        "autonomy_percentage": round(float(autonomy_percentage), 2),
        "checkpoint_count": checkpoint_count,
        "blocked_action_count": blocked_action_count,
        "receipt_count": receipt_count,
        "estimated_minutes_saved": round(float(estimated_minutes_saved), 2),
        "outcome_packet_hash": outcome_packet_hash,
        "ets_preview_hash": ets_preview_hash,
        "no_payment_created": True,
        "no_booking_created": True,
        "no_external_message_sent": True,
        "no_live_reputation_mutation": True,
        "no_unapproved_deploy": True,
        "narrative_hash": "",
    }
    narrative["narrative_hash"] = _hash({k: v for k, v in narrative.items() if k != "narrative_hash"})
    return narrative


def compile_blocked_action_demo_metrics(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    blocked_actions: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized = []

    for action in blocked_actions:
        action_type = action.get("action_type")
        reason = action.get("reason")
        safe_alternative = action.get("safe_alternative")

        if not action_type or not reason:
            raise ValueError("blocked action requires action_type and reason")

        normalized.append({
            "action_type": action_type,
            "reason": reason,
            "what_would_have_happened": action.get("what_would_have_happened", "not_recorded"),
            "safe_alternative": safe_alternative or "pause_for_human_review",
            "risk_level": action.get("risk_level", "high"),
        })

    normalized = sorted(normalized, key=lambda item: (item["action_type"], item["reason"]))

    metrics = {
        "schema_version": "aion.blocked_action_demo_metrics.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "blocked_action_count": len(normalized),
        "blocked_actions": normalized,
        "metrics_hash": "",
    }
    metrics["metrics_hash"] = _hash({k: v for k, v in metrics.items() if k != "metrics_hash"})
    return metrics


def create_reputation_governance_requirement(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    agent_id: str,
    ets_preview_hash: str,
    requested_live_mutation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(ets_preview_hash, str) or not ets_preview_hash.startswith("sha256:"):
        raise ValueError("ets_preview_hash must be sha256-prefixed")

    requested_live_mutation = requested_live_mutation or {}
    guard = assert_reputation_preview_only(requested_live_mutation)

    requirement = {
        "schema_version": "aion.reputation_governance_requirement.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "agent_id": agent_id,
        "ets_preview_hash": ets_preview_hash,
        "governance_required_before_live_mutation": True,
        "live_mutation_allowed_now": False,
        "guard_hash": guard["guard_hash"],
        "guard_allowed": guard["allowed"],
        "requirement_state": "governance_required",
        "requirement_hash": "",
    }
    requirement["requirement_hash"] = _hash({k: v for k, v in requirement.items() if k != "requirement_hash"})
    return requirement


def compile_demo_summary_packet(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    narrative: dict[str, Any],
    blocked_metrics: dict[str, Any],
    governance_requirement: dict[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []

    expected_narrative_hash = _hash({k: v for k, v in narrative.items() if k != "narrative_hash"})
    if narrative.get("narrative_hash") != expected_narrative_hash:
        reasons.append("narrative_hash_mismatch")

    expected_blocked_hash = _hash({k: v for k, v in blocked_metrics.items() if k != "metrics_hash"})
    if blocked_metrics.get("metrics_hash") != expected_blocked_hash:
        reasons.append("blocked_metrics_hash_mismatch")

    expected_req_hash = _hash({k: v for k, v in governance_requirement.items() if k != "requirement_hash"})
    if governance_requirement.get("requirement_hash") != expected_req_hash:
        reasons.append("governance_requirement_hash_mismatch")

    if narrative.get("required_visible_message") != REQUIRED_DEMO_MESSAGE:
        reasons.append("required_demo_message_missing")

    if narrative.get("no_live_reputation_mutation") is not True:
        reasons.append("live_reputation_mutation_not_blocked")

    if governance_requirement.get("live_mutation_allowed_now") is not False:
        reasons.append("governance_requirement_allows_live_mutation")

    for obj_name, obj in {
        "narrative": narrative,
        "blocked_metrics": blocked_metrics,
        "governance_requirement": governance_requirement,
    }.items():
        if obj.get("mission_id") != mission_id:
            reasons.append(f"{obj_name}_mission_id_mismatch")
        if obj.get("mission_run_id") != mission_run_id:
            reasons.append(f"{obj_name}_mission_run_id_mismatch")
        if obj.get("business_id") != business_id:
            reasons.append(f"{obj_name}_business_id_mismatch")

    allowed = not reasons

    packet = {
        "schema_version": "aion.demo_summary_packet.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "visible_message": REQUIRED_DEMO_MESSAGE,
        "narrative_hash": narrative.get("narrative_hash"),
        "blocked_metrics_hash": blocked_metrics.get("metrics_hash"),
        "governance_requirement_hash": governance_requirement.get("requirement_hash"),
        "allowed": allowed,
        "summary_state": "demo_summary_ready" if allowed else "demo_summary_blocked",
        "reasons": reasons,
        "summary_hash": "",
    }
    packet["summary_hash"] = _hash({k: v for k, v in packet.items() if k != "summary_hash"})
    return packet
