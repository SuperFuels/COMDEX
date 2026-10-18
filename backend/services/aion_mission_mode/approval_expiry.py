"""
AION Phase 20R — Approval Expiry Handling

Contract:
- Expired approvals cannot execute.
- Expired approvals invalidate pending action payloads.
- Changed or expired payloads require fresh approval.
- Runtime pauses at approval expiry.
- Boardroom receives user-facing expiry state.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Any

from backend.services.aion_mission_mode.canonical_payload_hashing import (
    payload_sha256_normalized,
)


@dataclass(frozen=True)
class ApprovalExpiryDecision:
    mission_id: str
    mission_run_id: str
    checkpoint_id: str
    step_id: str
    action_type: str
    approval_hash: str
    approved_payload_hash: str
    current_payload_hash: str
    expires_at: str | None
    now_iso: str
    approval_expired: bool
    payload_changed: bool
    approval_valid: bool
    runtime_state: str
    event_type: str
    requires_fresh_approval: bool
    user_explanation: str
    boardroom_message: str
    decision_hash: str = ""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def is_approval_expired(*, expires_at: str | None, now_iso: str) -> bool:
    if not expires_at:
        return False
    return str(now_iso) > str(expires_at)


def evaluate_approval_expiry(
    *,
    mission_id: str,
    mission_run_id: str,
    checkpoint_id: str,
    step_id: str,
    action_type: str,
    approval_hash: str,
    approved_payload_hash: str,
    current_payload: dict[str, Any],
    expires_at: str | None,
    now_iso: str,
) -> dict[str, Any]:
    current_payload_hash = payload_sha256_normalized(current_payload)
    expired = is_approval_expired(expires_at=expires_at, now_iso=now_iso)
    changed = approved_payload_hash != current_payload_hash
    valid = (not expired) and (not changed)

    if valid:
        runtime_state = "approval_valid_execution_allowed"
        event_type = "approval_valid"
        explanation = "Approval is valid for this exact payload."
        boardroom = "Approved payload is unchanged and approval has not expired."
    elif expired:
        runtime_state = "paused_at_checkpoint"
        event_type = "approval_expired"
        explanation = "Approval has expired. Fresh approval is required before this action can continue."
        boardroom = "Approval expired; payload approval is no longer valid."
    else:
        runtime_state = "paused_at_checkpoint"
        event_type = "approval_payload_changed"
        explanation = "Approval applies to the exact message or payload only. This payload changed and needs fresh approval."
        boardroom = "Payload changed; approval no longer valid."

    decision = ApprovalExpiryDecision(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        checkpoint_id=checkpoint_id,
        step_id=step_id,
        action_type=action_type,
        approval_hash=approval_hash,
        approved_payload_hash=approved_payload_hash,
        current_payload_hash=current_payload_hash,
        expires_at=expires_at,
        now_iso=now_iso,
        approval_expired=expired,
        payload_changed=changed,
        approval_valid=valid,
        runtime_state=runtime_state,
        event_type=event_type,
        requires_fresh_approval=not valid,
        user_explanation=explanation,
        boardroom_message=boardroom,
    )

    data = asdict(decision)
    data["decision_hash"] = _hash({k: v for k, v in data.items() if k != "decision_hash"})
    return data


def invalidate_pending_payload_if_expired(decision: dict[str, Any]) -> dict[str, Any]:
    if decision.get("approval_expired") is True:
        return {
            "pending_payload_valid": False,
            "runtime_state": "paused_at_checkpoint",
            "event_type": "approval_expired",
            "requires_fresh_approval": True,
            "reason": "expired_approval_invalidates_pending_action_payload",
            "decision_hash": decision.get("decision_hash"),
        }

    return {
        "pending_payload_valid": not decision.get("payload_changed", False),
        "runtime_state": decision.get("runtime_state"),
        "event_type": decision.get("event_type"),
        "requires_fresh_approval": decision.get("requires_fresh_approval", False),
        "reason": "approval_not_expired",
        "decision_hash": decision.get("decision_hash"),
    }


def boardroom_expiry_notice(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "mission_id": decision["mission_id"],
        "mission_run_id": decision["mission_run_id"],
        "checkpoint_id": decision["checkpoint_id"],
        "step_id": decision["step_id"],
        "action_type": decision["action_type"],
        "event_type": decision["event_type"],
        "approval_valid": decision["approval_valid"],
        "requires_fresh_approval": decision["requires_fresh_approval"],
        "message": decision["boardroom_message"],
        "user_explanation": decision["user_explanation"],
        "show_payload_changed": decision["payload_changed"],
        "show_approval_expired": decision["approval_expired"],
        "controls_enabled": decision["approval_valid"],
    }


def create_atomic_time_anchor(*, eval_time: str) -> dict[str, Any]:
    """
    Create a single immutable checkpoint evaluation timestamp.

    The runtime must use this timestamp for every assertion inside the same
    checkpoint validation frame.
    """
    anchor = {
        "schema_version": "aion.approval_time_anchor.v0",
        "time_source": "monotonic_or_trusted_reference",
        "t_eval": str(eval_time),
        "immutable_within_checkpoint": True,
    }
    anchor["time_anchor_hash"] = _hash(anchor)
    return anchor


def temporal_decision_hash(
    *,
    approved_payload_hash: str,
    current_payload_hash: str,
    t_eval: str,
    payload_changed: bool,
    approval_expired: bool,
    runtime_state: str,
    event_type: str,
    checkpoint_id: str,
) -> str:
    return _hash(
        {
            "approved_payload_hash": approved_payload_hash,
            "current_payload_hash": current_payload_hash,
            "t_eval": t_eval,
            "state_flags": {
                "payload_changed": payload_changed,
                "approval_expired": approval_expired,
            },
            "runtime_state": runtime_state,
            "event_type": event_type,
            "checkpoint_id": checkpoint_id,
        }
    )


def evaluate_approval_expiry_with_time_anchor(
    *,
    mission_id: str,
    mission_run_id: str,
    checkpoint_id: str,
    step_id: str,
    action_type: str,
    approval_hash: str,
    approved_payload_hash: str,
    current_payload: dict[str, Any],
    expires_at: str | None,
    time_anchor: dict[str, Any],
) -> dict[str, Any]:
    if time_anchor.get("immutable_within_checkpoint") is not True:
        raise ValueError("approval_time_anchor_must_be_immutable")

    t_eval = str(time_anchor.get("t_eval", ""))

    decision = evaluate_approval_expiry(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        checkpoint_id=checkpoint_id,
        step_id=step_id,
        action_type=action_type,
        approval_hash=approval_hash,
        approved_payload_hash=approved_payload_hash,
        current_payload=current_payload,
        expires_at=expires_at,
        now_iso=t_eval,
    )

    decision["t_eval"] = t_eval
    decision["time_anchor_hash"] = time_anchor.get("time_anchor_hash")
    decision["decision_hash"] = temporal_decision_hash(
        approved_payload_hash=decision["approved_payload_hash"],
        current_payload_hash=decision["current_payload_hash"],
        t_eval=t_eval,
        payload_changed=decision["payload_changed"],
        approval_expired=decision["approval_expired"],
        runtime_state=decision["runtime_state"],
        event_type=decision["event_type"],
        checkpoint_id=checkpoint_id,
    )
    return decision


def verify_time_anchor_not_resampled(
    *,
    initial_time_anchor: dict[str, Any],
    runtime_time_anchor: dict[str, Any],
) -> bool:
    return (
        initial_time_anchor.get("t_eval") == runtime_time_anchor.get("t_eval")
        and initial_time_anchor.get("time_anchor_hash") == runtime_time_anchor.get("time_anchor_hash")
        and initial_time_anchor.get("immutable_within_checkpoint") is True
        and runtime_time_anchor.get("immutable_within_checkpoint") is True
    )
