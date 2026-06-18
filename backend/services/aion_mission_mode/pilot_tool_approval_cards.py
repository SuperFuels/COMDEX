"""
AION Phase 23U — Pilot Tool Approval Cards

Purpose:
- Create exact-payload approval cards for blocked live tool execution items.
- Verify approval hash, approved payload hash, expiry and current payload hash.
- Rebuild the tool execution item through the existing External Tool Gateway.
- Never execute live external side effects in this layer.
"""

from __future__ import annotations

from typing import Any

from backend.services.aion_mission_mode.department_capability_map import stable_hash
from backend.services.aion_mission_mode.pilot_tool_execution_queue import create_tool_execution_item


def _hash_without(payload: dict[str, Any], excluded_key: str) -> str:
    return stable_hash({k: v for k, v in payload.items() if k != excluded_key})


def create_exact_payload_approval_card(
    *,
    tool_execution_item: dict[str, Any],
    requested_by: str = "aion_pilot",
    approval_expires_at: int | None = None,
) -> dict[str, Any]:
    if not tool_execution_item:
        raise ValueError("tool_execution_item is required")

    if tool_execution_item.get("tool_mode") != "approved_live_external":
        raise ValueError("approval cards are only required for approved_live_external tool items")

    payload_hash = tool_execution_item.get("payload_hash")
    if not isinstance(payload_hash, str) or not payload_hash.startswith("sha256:"):
        raise ValueError("tool_execution_item payload_hash is required")

    card = {
        "schema_version": "aion.pilot_tool_exact_payload_approval_card.v0",
        "business_id": tool_execution_item.get("business_id"),
        "mission_id": tool_execution_item.get("mission_id"),
        "mission_run_id": tool_execution_item.get("mission_run_id"),
        "department_id": tool_execution_item.get("department_id"),
        "department_display_name": tool_execution_item.get("department_display_name"),
        "task_id": tool_execution_item.get("task_id"),
        "title": tool_execution_item.get("title"),
        "department_capability": tool_execution_item.get("department_capability"),
        "gateway_tool_name": tool_execution_item.get("gateway_tool_name"),
        "local_tool_id": tool_execution_item.get("local_tool_id"),
        "tool_mode": tool_execution_item.get("tool_mode"),
        "tool_execution_item_hash": tool_execution_item.get("tool_execution_item_hash"),
        "approval_type": "exact_payload_approval",
        "expected_payload_hash": payload_hash,
        "approval_expires_at": approval_expires_at,
        "requested_by": requested_by,
        "approval_required": True,
        "approval_state": "waiting_exact_payload_approval",
        "live_execution_allowed": False,
        "external_side_effect_executed": False,
        "approval_card_hash": "",
    }
    card["approval_card_hash"] = _hash_without(card, "approval_card_hash")
    return card


def create_exact_payload_approval_decision(
    *,
    approval_card: dict[str, Any],
    approved: bool,
    approved_by: str = "human_operator",
    approved_payload_hash: str | None = None,
    approval_time: int = 0,
    approval_expires_at: int | None = None,
) -> dict[str, Any]:
    expected_payload_hash = approval_card.get("expected_payload_hash")
    if not expected_payload_hash:
        raise ValueError("approval_card expected_payload_hash is required")

    decision = {
        "schema_version": "aion.pilot_tool_exact_payload_approval_decision.v0",
        "approval_card_hash": approval_card.get("approval_card_hash"),
        "business_id": approval_card.get("business_id"),
        "mission_id": approval_card.get("mission_id"),
        "mission_run_id": approval_card.get("mission_run_id"),
        "department_id": approval_card.get("department_id"),
        "task_id": approval_card.get("task_id"),
        "gateway_tool_name": approval_card.get("gateway_tool_name"),
        "approval_type": "exact_payload_approval",
        "approved": bool(approved),
        "approved_by": approved_by,
        "approved_payload_hash": approved_payload_hash or expected_payload_hash,
        "expected_payload_hash": expected_payload_hash,
        "approval_time": int(approval_time),
        "approval_expires_at": (
            approval_expires_at
            if approval_expires_at is not None
            else approval_card.get("approval_expires_at")
        ),
        "external_side_effect_executed": False,
        "approval_hash": "",
    }
    decision["approval_hash"] = _hash_without(decision, "approval_hash")
    return decision


def evaluate_exact_payload_approval(
    *,
    approval_card: dict[str, Any],
    approval_decision: dict[str, Any] | None,
    current_payload_hash: str | None = None,
    evaluation_time: int = 0,
) -> dict[str, Any]:
    decision = approval_decision or {}
    expected_payload_hash = approval_card.get("expected_payload_hash")
    approved_payload_hash = decision.get("approved_payload_hash")
    approval_expires_at = decision.get("approval_expires_at")
    current_payload_hash = current_payload_hash or expected_payload_hash

    reasons: list[str] = []

    if not approval_card.get("approval_card_hash"):
        reasons.append("missing_approval_card_hash")

    if decision.get("approval_card_hash") != approval_card.get("approval_card_hash"):
        reasons.append("approval_card_hash_mismatch")

    if decision.get("approval_type") != "exact_payload_approval":
        reasons.append("approval_type_mismatch")

    if decision.get("approved") is not True:
        reasons.append("approval_not_granted")

    if not approved_payload_hash:
        reasons.append("missing_approved_payload_hash")
    elif approved_payload_hash != expected_payload_hash:
        reasons.append("approved_payload_hash_mismatch")

    if current_payload_hash != expected_payload_hash:
        reasons.append("current_payload_hash_mismatch_requires_fresh_approval")

    if not decision.get("approval_hash"):
        reasons.append("missing_approval_hash")

    if approval_expires_at is None:
        reasons.append("missing_approval_expiry")
    elif int(evaluation_time) > int(approval_expires_at):
        reasons.append("approval_expired")

    allowed = not reasons

    result = {
        "schema_version": "aion.pilot_tool_exact_payload_approval_evaluation.v0",
        "business_id": approval_card.get("business_id"),
        "mission_id": approval_card.get("mission_id"),
        "mission_run_id": approval_card.get("mission_run_id"),
        "department_id": approval_card.get("department_id"),
        "task_id": approval_card.get("task_id"),
        "gateway_tool_name": approval_card.get("gateway_tool_name"),
        "approval_card_hash": approval_card.get("approval_card_hash"),
        "approval_hash": decision.get("approval_hash"),
        "expected_payload_hash": expected_payload_hash,
        "approved_payload_hash": approved_payload_hash,
        "current_payload_hash": current_payload_hash,
        "approval_expires_at": approval_expires_at,
        "evaluation_time": int(evaluation_time),
        "allowed": allowed,
        "approval_state": "exact_payload_approval_valid" if allowed else "exact_payload_approval_blocked",
        "reasons": reasons,
        "external_side_effect_executed": False,
        "live_execution_allowed": False,
        "approval_evaluation_hash": "",
    }
    result["approval_evaluation_hash"] = _hash_without(result, "approval_evaluation_hash")
    return result


def apply_exact_payload_approval_to_tool_execution_item(
    *,
    tool_execution_item: dict[str, Any],
    approval_card: dict[str, Any],
    approval_decision: dict[str, Any],
    evaluation_time: int,
) -> dict[str, Any]:
    approval_evaluation = evaluate_exact_payload_approval(
        approval_card=approval_card,
        approval_decision=approval_decision,
        current_payload_hash=tool_execution_item.get("payload_hash"),
        evaluation_time=evaluation_time,
    )

    if not approval_evaluation["allowed"]:
        result = {
            **tool_execution_item,
            "exact_payload_approval": approval_evaluation,
            "gateway_allowed": False,
            "gateway_state": "blocked",
            "status": "waiting_approval",
            "execution_allowed": False,
            "live_execution_allowed": False,
            "external_side_effect_executed": False,
        }
        result["tool_execution_item_hash"] = stable_hash(
            {k: v for k, v in result.items() if k != "tool_execution_item_hash"}
        )
        return result

    queue_item = {
        "business_id": tool_execution_item.get("business_id"),
        "mission_id": tool_execution_item.get("mission_id"),
        "mission_run_id": tool_execution_item.get("mission_run_id"),
        "department_id": tool_execution_item.get("department_id"),
        "department_display_name": tool_execution_item.get("department_display_name"),
        "task_id": tool_execution_item.get("task_id"),
        "title": tool_execution_item.get("title"),
        "task_type": tool_execution_item.get("task_type"),
        "capability": tool_execution_item.get("department_capability"),
        "concrete_tool_id": tool_execution_item.get("local_tool_id"),
        "permission": tool_execution_item.get("permission"),
        "approval_required": tool_execution_item.get("approval_required"),
        "credential_required": tool_execution_item.get("credential_required"),
        "live_external_side_effect": tool_execution_item.get("live_external_side_effect"),
        "artifact_type": tool_execution_item.get("artifact_type"),
    }

    approved_item = create_tool_execution_item(
        queue_item=queue_item,
        evaluation_time=evaluation_time,
        approved_payload_hash=approval_evaluation["approved_payload_hash"],
        approval_hash=approval_evaluation["approval_hash"],
        approval_expires_at=approval_evaluation["approval_expires_at"],
    )

    approved_item["exact_payload_approval"] = approval_evaluation
    approved_item["approval_card_hash"] = approval_card.get("approval_card_hash")
    approved_item["approval_hash"] = approval_evaluation["approval_hash"]
    approved_item["live_execution_allowed"] = False
    approved_item["execution_allowed"] = False
    approved_item["external_side_effect_executed"] = False
    approved_item["status"] = "waiting_live_executor"

    approved_item["tool_execution_item_hash"] = stable_hash(
        {k: v for k, v in approved_item.items() if k != "tool_execution_item_hash"}
    )
    return approved_item
