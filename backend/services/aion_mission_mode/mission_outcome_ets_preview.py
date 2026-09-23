from __future__ import annotations

from hashlib import sha256
import json
from typing import Any


VALID_OUTCOME_CATEGORIES = {
    "fully_autonomous_success",
    "checkpointed_success",
    "human_guided_success",
    "partial_failure",
    "blocked_for_safety",
}

VALID_ETS_STATES = {
    "preview_only",
    "live_mutation_blocked",
}

LIVE_REPUTATION_MUTATION_FIELDS = {
    "write_live_reputation",
    "mutate_agent_score",
    "commit_ets",
    "publish_trust_score",
    "update_public_reputation",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def classify_mission_outcome(
    *,
    completed_steps: int,
    failed_steps: int,
    blocked_for_safety_count: int,
    human_approval_count: int,
    human_task_count: int,
    total_steps: int,
) -> str:
    if total_steps <= 0:
        raise ValueError("total_steps must be positive")

    if blocked_for_safety_count > 0:
        return "blocked_for_safety"

    if failed_steps > 0:
        return "partial_failure"

    if completed_steps >= total_steps and human_task_count > 0:
        return "human_guided_success"

    if completed_steps >= total_steps and human_approval_count > 0:
        return "checkpointed_success"

    if completed_steps >= total_steps:
        return "fully_autonomous_success"

    return "partial_failure"


def compile_mission_outcome_metrics(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    total_steps: int,
    completed_steps: int,
    autonomous_steps: int,
    human_approval_count: int,
    human_task_count: int,
    blocked_action_count: int,
    receipt_count: int,
    failed_steps: int = 0,
    estimated_minutes_saved: float = 0.0,
) -> dict[str, Any]:
    if total_steps <= 0:
        raise ValueError("total_steps must be positive")

    if completed_steps < 0 or autonomous_steps < 0:
        raise ValueError("step counts must be non-negative")

    if autonomous_steps > total_steps:
        raise ValueError("autonomous_steps cannot exceed total_steps")

    autonomy_percentage = round((autonomous_steps / total_steps) * 100, 2)

    outcome_category = classify_mission_outcome(
        completed_steps=completed_steps,
        failed_steps=failed_steps,
        blocked_for_safety_count=blocked_action_count,
        human_approval_count=human_approval_count,
        human_task_count=human_task_count,
        total_steps=total_steps,
    )

    metrics = {
        "schema_version": "aion.mission_outcome_metrics.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "total_steps": total_steps,
        "completed_steps": completed_steps,
        "autonomous_steps": autonomous_steps,
        "autonomy_percentage": autonomy_percentage,
        "human_approval_count": human_approval_count,
        "human_task_count": human_task_count,
        "blocked_action_count": blocked_action_count,
        "receipt_count": receipt_count,
        "failed_steps": failed_steps,
        "estimated_minutes_saved": round(float(estimated_minutes_saved), 2),
        "outcome_category": outcome_category,
        "metrics_hash": "",
    }
    metrics["metrics_hash"] = _hash({k: v for k, v in metrics.items() if k != "metrics_hash"})
    return metrics


def create_ets_preview(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    agent_id: str,
    outcome_metrics_hash: str,
    receipt_hashes: list[str],
    proof_hash: str,
    replay_packet_hash: str,
    proposed_score_delta: float,
    rationale: str,
) -> dict[str, Any]:
    for name, value in {
        "outcome_metrics_hash": outcome_metrics_hash,
        "proof_hash": proof_hash,
        "replay_packet_hash": replay_packet_hash,
    }.items():
        if not isinstance(value, str) or not value.startswith("sha256:"):
            raise ValueError(f"{name} must be sha256-prefixed")

    sorted_receipts = sorted(receipt_hashes)
    for receipt_hash in sorted_receipts:
        if not isinstance(receipt_hash, str) or not receipt_hash.startswith("sha256:"):
            raise ValueError("receipt_hashes must be sha256-prefixed")

    preview = {
        "schema_version": "aion.ets_preview.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "agent_id": agent_id,
        "ets_state": "preview_only",
        "live_reputation_mutation_allowed": False,
        "outcome_metrics_hash": outcome_metrics_hash,
        "receipt_hashes": sorted_receipts,
        "proof_hash": proof_hash,
        "replay_packet_hash": replay_packet_hash,
        "proposed_score_delta": round(float(proposed_score_delta), 4),
        "rationale": rationale,
        "ets_preview_hash": "",
    }
    preview["ets_preview_hash"] = _hash({k: v for k, v in preview.items() if k != "ets_preview_hash"})
    return preview


def assert_no_live_reputation_mutation(payload: dict[str, Any]) -> dict[str, Any]:
    violations: list[str] = []

    for field in LIVE_REPUTATION_MUTATION_FIELDS:
        if payload.get(field):
            violations.append(f"live_reputation_mutation_field_blocked:{field}")

    if payload.get("ets_state") not in {None, "preview_only"}:
        violations.append("ets_state_not_preview_only")

    allowed = not violations

    result = {
        "schema_version": "aion.ets_mutation_guard.v0",
        "allowed": allowed,
        "guard_state": "ets_preview_only_verified" if allowed else "live_mutation_blocked",
        "violations": violations,
        "guard_hash": "",
    }
    result["guard_hash"] = _hash({k: v for k, v in result.items() if k != "guard_hash"})
    return result


def compile_outcome_packet(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    metrics: dict[str, Any],
    ets_preview: dict[str, Any],
    replay_packet_hash: str,
    proof_hash: str,
) -> dict[str, Any]:
    reasons: list[str] = []

    expected_metrics_hash = _hash({k: v for k, v in metrics.items() if k != "metrics_hash"})
    if metrics.get("metrics_hash") != expected_metrics_hash:
        reasons.append("metrics_hash_mismatch")

    expected_ets_hash = _hash({k: v for k, v in ets_preview.items() if k != "ets_preview_hash"})
    if ets_preview.get("ets_preview_hash") != expected_ets_hash:
        reasons.append("ets_preview_hash_mismatch")

    if ets_preview.get("ets_state") != "preview_only":
        reasons.append("ets_not_preview_only")

    if ets_preview.get("live_reputation_mutation_allowed") is not False:
        reasons.append("live_reputation_mutation_not_blocked")

    for name, value in {
        "replay_packet_hash": replay_packet_hash,
        "proof_hash": proof_hash,
    }.items():
        if not isinstance(value, str) or not value.startswith("sha256:"):
            reasons.append(f"invalid_{name}")

    for obj_name, obj in {"metrics": metrics, "ets_preview": ets_preview}.items():
        if obj.get("mission_id") != mission_id:
            reasons.append(f"{obj_name}_mission_id_mismatch")
        if obj.get("mission_run_id") != mission_run_id:
            reasons.append(f"{obj_name}_mission_run_id_mismatch")
        if obj.get("business_id") != business_id:
            reasons.append(f"{obj_name}_business_id_mismatch")

    allowed = not reasons

    packet = {
        "schema_version": "aion.mission_outcome_packet.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "outcome_category": metrics.get("outcome_category"),
        "autonomy_percentage": metrics.get("autonomy_percentage"),
        "blocked_action_count": metrics.get("blocked_action_count"),
        "receipt_count": metrics.get("receipt_count"),
        "estimated_minutes_saved": metrics.get("estimated_minutes_saved"),
        "metrics_hash": metrics.get("metrics_hash"),
        "ets_preview_hash": ets_preview.get("ets_preview_hash"),
        "replay_packet_hash": replay_packet_hash,
        "proof_hash": proof_hash,
        "allowed": allowed,
        "packet_state": "mission_outcome_packet_ready" if allowed else "mission_outcome_packet_blocked",
        "reasons": reasons,
        "packet_hash": "",
    }
    packet["packet_hash"] = _hash({k: v for k, v in packet.items() if k != "packet_hash"})
    return packet
