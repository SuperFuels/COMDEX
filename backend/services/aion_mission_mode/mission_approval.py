"""
AION Phase 20F — Mission Approval + Checkpoint Approval Split

Contract:
- Mission approval approves boundary conditions only.
- Checkpoint approval approves one exact immutable payload hash only.
- Broad/unbound checkpoint approval is rejected.
- Edited payloads invalidate checkpoint approval.
- Approval hashes are deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Any


VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}


@dataclass(frozen=True)
class MissionApproval:
    mission_id: str
    mission_run_id: str
    approved_by: str
    approved: bool
    approved_contract_hash: str
    approved_lanes: tuple[str, ...]
    approved_hard_blocked_lanes: tuple[str, ...]
    max_runtime_seconds: int
    max_tool_calls: int
    max_cost: float
    approval_scope: str = "mission_boundary_only"
    live_side_effects_enabled: bool = False
    approval_hash: str = ""


@dataclass(frozen=True)
class CheckpointApproval:
    mission_id: str
    mission_run_id: str
    checkpoint_id: str
    step_id: str
    approved_by: str
    approved: bool
    payload_hash: str
    action_type: str
    risk_level: str
    expires_at: str | None = None
    approval_scope: str = "exact_payload_only"
    approval_hash: str = ""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_payload_hash(payload: dict[str, Any]) -> str:
    return "sha256:" + sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _hash(value: Any) -> str:
    return canonical_payload_hash(value)


def create_mission_approval(
    *,
    mission_id: str,
    mission_run_id: str,
    approved_by: str,
    approved: bool,
    approved_contract_hash: str,
    approved_lanes: list[str] | tuple[str, ...],
    approved_hard_blocked_lanes: list[str] | tuple[str, ...],
    max_runtime_seconds: int,
    max_tool_calls: int,
    max_cost: float,
) -> dict[str, Any]:
    approval = MissionApproval(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        approved_by=approved_by,
        approved=approved,
        approved_contract_hash=approved_contract_hash,
        approved_lanes=tuple(approved_lanes),
        approved_hard_blocked_lanes=tuple(approved_hard_blocked_lanes),
        max_runtime_seconds=max_runtime_seconds,
        max_tool_calls=max_tool_calls,
        max_cost=max_cost,
    )
    data = asdict(approval)
    data["approval_hash"] = _hash({k: v for k, v in data.items() if k != "approval_hash"})
    return data


def create_checkpoint_approval(
    *,
    mission_id: str,
    mission_run_id: str,
    checkpoint_id: str,
    step_id: str,
    approved_by: str,
    approved: bool,
    payload_hash: str,
    action_type: str,
    risk_level: str,
    expires_at: str | None = None,
) -> dict[str, Any]:
    if not payload_hash or not str(payload_hash).startswith("sha256:"):
        raise ValueError("checkpoint_approval_requires_exact_payload_hash")

    if risk_level not in VALID_RISK_LEVELS:
        raise ValueError(f"invalid_risk_level:{risk_level}")

    approval = CheckpointApproval(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        checkpoint_id=checkpoint_id,
        step_id=step_id,
        approved_by=approved_by,
        approved=approved,
        payload_hash=payload_hash,
        action_type=action_type,
        risk_level=risk_level,
        expires_at=expires_at,
    )
    data = asdict(approval)
    data["approval_hash"] = _hash({k: v for k, v in data.items() if k != "approval_hash"})
    return data


def validate_mission_approval_scope(approval: dict[str, Any]) -> bool:
    return (
        approval.get("approval_scope") == "mission_boundary_only"
        and bool(approval.get("approved_contract_hash"))
        and approval.get("live_side_effects_enabled") is False
        and "payload_hash" not in approval
    )


def validate_checkpoint_approval_scope(approval: dict[str, Any]) -> bool:
    return (
        approval.get("approval_scope") == "exact_payload_only"
        and bool(approval.get("payload_hash"))
        and str(approval.get("payload_hash")).startswith("sha256:")
        and bool(approval.get("checkpoint_id"))
        and bool(approval.get("step_id"))
        and bool(approval.get("action_type"))
        and approval.get("risk_level") in VALID_RISK_LEVELS
    )


def validate_checkpoint_payload_unchanged(
    *,
    approval: dict[str, Any],
    current_payload: dict[str, Any],
) -> bool:
    return approval.get("payload_hash") == canonical_payload_hash(current_payload)


def reject_broad_checkpoint_approval(approval: dict[str, Any]) -> bool:
    """
    Returns True if approval must be rejected as broad/unbound.
    """
    if approval.get("approval_scope") != "exact_payload_only":
        return True

    if not approval.get("payload_hash"):
        return True

    if approval.get("payload_hash") in {"*", "any", "all", "approved"}:
        return True

    if not str(approval.get("payload_hash")).startswith("sha256:"):
        return True

    return False


def approval_expired(*, approval: dict[str, Any], now_iso: str) -> bool:
    expires_at = approval.get("expires_at")
    if not expires_at:
        return False
    return str(now_iso) > str(expires_at)
