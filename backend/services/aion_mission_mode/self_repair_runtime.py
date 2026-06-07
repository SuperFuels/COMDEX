"""
AION Phase 20W — Fault Tolerance + Self-Repair Runtime

Contract:
- Repair is allowed only for safe internal/preview lanes.
- Max 2 repair attempts.
- Repair cannot call live/external/raw tools.
- Repair cannot change an action into an unsafe lane.
- Failed repair transitions to waiting_human_review.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from hashlib import sha256
import json
from typing import Any


SAFE_REPAIR_LANES = {"research", "creation", "internal_ops"}

FORBIDDEN_REPAIR_LANES = {
    "external_action",
    "financial_action",
    "legal_action",
    "deployment_action",
    "memory_mutation",
}

FORBIDDEN_REPAIR_ACTIONS = {
    "send_email",
    "send_email_live",
    "send_whatsapp",
    "send_whatsapp_live",
    "send_customer_message",
    "publish_advert",
    "post_social",
    "spend_money",
    "take_payment",
    "capture_payment_live",
    "create_booking",
    "create_booking_live",
    "create_escrow",
    "release_escrow",
    "dispatch_worker",
    "deploy_live_page",
    "deploy_production_live",
    "raw_terminal_exec",
    "mutate_business_memory",
    "write_live_reputation",
}


@dataclass(frozen=True)
class RepairAttemptInput:
    mission_id: str
    mission_run_id: str
    step_id: str
    action_type: str
    lane: str
    error_type: str
    error_message: str
    payload: dict[str, Any]
    trace_context: dict[str, Any] = field(default_factory=dict)
    attempt_index: int = 1


@dataclass(frozen=True)
class RepairAttemptResult:
    mission_id: str
    mission_run_id: str
    step_id: str
    action_type: str
    lane: str
    attempt_index: int
    repair_allowed: bool
    repair_succeeded: bool
    runtime_state: str
    reason: str
    repaired_payload: dict[str, Any]
    repair_hash: str
    live_side_effects_enabled: bool = False


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _slug(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def is_safe_repair_lane(lane: str) -> bool:
    return _slug(lane) in SAFE_REPAIR_LANES


def is_forbidden_repair_action(action_type: str) -> bool:
    return _slug(action_type) in FORBIDDEN_REPAIR_ACTIONS


def validate_repair_attempt_allowed(attempt: RepairAttemptInput) -> tuple[bool, str]:
    lane = _slug(attempt.lane)
    action = _slug(attempt.action_type)

    if attempt.attempt_index < 1:
        return False, "invalid_attempt_index"

    if attempt.attempt_index > 2:
        return False, "max_repair_attempts_exceeded"

    if lane in FORBIDDEN_REPAIR_LANES:
        return False, f"repair_forbidden_lane:{lane}"

    if lane not in SAFE_REPAIR_LANES:
        return False, f"repair_unknown_lane:{lane}"

    if action in FORBIDDEN_REPAIR_ACTIONS:
        return False, f"repair_forbidden_action:{action}"

    return True, "repair_allowed_safe_internal_lane"


def _deterministic_payload_repair(payload: dict[str, Any]) -> dict[str, Any]:
    repaired = dict(payload)

    # Safe schema-only fixes.
    if "title" in repaired and repaired["title"] is None:
        repaired["title"] = ""

    if "description" in repaired and repaired["description"] is None:
        repaired["description"] = ""

    if "draft" not in repaired and "content" in repaired:
        repaired["draft"] = repaired["content"]

    repaired["repair_metadata"] = {
        "repair_mode": "deterministic_schema_patch",
        "live_side_effects_enabled": False,
    }

    return repaired


def run_repair_attempt(attempt: RepairAttemptInput) -> dict[str, Any]:
    allowed, reason = validate_repair_attempt_allowed(attempt)

    if not allowed:
        result = RepairAttemptResult(
            mission_id=attempt.mission_id,
            mission_run_id=attempt.mission_run_id,
            step_id=attempt.step_id,
            action_type=_slug(attempt.action_type),
            lane=_slug(attempt.lane),
            attempt_index=attempt.attempt_index,
            repair_allowed=False,
            repair_succeeded=False,
            runtime_state="waiting_human_review",
            reason=reason,
            repaired_payload=dict(attempt.payload),
            repair_hash="",
        )
        data = asdict(result)
        data["repair_hash"] = _hash(data)
        return data

    repaired_payload = _deterministic_payload_repair(attempt.payload)

    result = RepairAttemptResult(
        mission_id=attempt.mission_id,
        mission_run_id=attempt.mission_run_id,
        step_id=attempt.step_id,
        action_type=_slug(attempt.action_type),
        lane=_slug(attempt.lane),
        attempt_index=attempt.attempt_index,
        repair_allowed=True,
        repair_succeeded=True,
        runtime_state="running_autonomous_steps",
        reason=reason,
        repaired_payload=repaired_payload,
        repair_hash="",
    )
    data = asdict(result)
    data["repair_hash"] = _hash(data)
    return data


def final_repair_failure_result(
    *,
    mission_id: str,
    mission_run_id: str,
    step_id: str,
    action_type: str,
    lane: str,
    attempts: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = {
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "step_id": step_id,
        "action_type": _slug(action_type),
        "lane": _slug(lane),
        "attempt_count": len(attempts),
        "runtime_state": "waiting_human_review",
        "repair_succeeded": False,
        "reason": "self_repair_failed_waiting_human_review",
        "attempt_hashes": [attempt.get("repair_hash") for attempt in attempts],
        "live_side_effects_enabled": False,
    }
    payload["failure_hash"] = _hash(payload)
    return payload
