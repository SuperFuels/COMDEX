"""
AION Phase 23P — Pilot Tool Execution Queue

Purpose:
- Converts department execution queue items into governed tool execution items.
- Uses the Pilot Capability Adapter.
- Uses the existing External Tool Gateway evaluation.
- Does not execute live tools.
- Does not grant raw model access to tools.

Design rule:
Departments own functional work.
Pilot coordinates.
The gateway permits or blocks.
Live side effects remain approval-gated.
"""

from __future__ import annotations

from typing import Any

from backend.services.aion_mission_mode.department_capability_map import stable_hash
from backend.services.aion_mission_mode.department_execution_queue import (
    add_blocked_live_action_cards,
    build_department_execution_queue,
)
from backend.services.aion_mission_mode.pilot_capability_adapter import (
    evaluate_department_queue_item_gateway_access,
)


def _tool_execution_status_from_gateway(*, queue_item: dict[str, Any], gateway_result: dict[str, Any]) -> str:
    if not gateway_result.get("adapted"):
        return "blocked"

    evaluation = gateway_result.get("gateway_evaluation") or {}

    if evaluation.get("allowed") is not True:
        return "waiting_approval" if queue_item.get("approval_required") is True else "blocked"

    tool_mode = evaluation.get("tool_mode")

    if tool_mode == "safe_internal":
        return "ready"

    if tool_mode == "read_only_external":
        return "ready"

    if tool_mode == "staged_external":
        return "staged"

    if tool_mode == "approved_live_external":
        return "waiting_approval"

    return "blocked"


def create_tool_execution_item(
    *,
    queue_item: dict[str, Any],
    evaluation_time: int,
    caller: str = "aion_pilot",
    approved_payload_hash: str | None = None,
    approval_hash: str | None = None,
    approval_expires_at: int | None = None,
) -> dict[str, Any]:
    gateway_result = evaluate_department_queue_item_gateway_access(
        queue_item=queue_item,
        evaluation_time=evaluation_time,
        caller=caller,
        approved_payload_hash=approved_payload_hash,
        approval_hash=approval_hash,
        approval_expires_at=approval_expires_at,
    )

    evaluation = gateway_result.get("gateway_evaluation") or {}
    reasons = list(evaluation.get("reasons") or [])

    status = _tool_execution_status_from_gateway(
        queue_item=queue_item,
        gateway_result=gateway_result,
    )

    item = {
        "schema_version": "aion.pilot_tool_execution_item.v0",
        "business_id": queue_item.get("business_id"),
        "mission_id": queue_item.get("mission_id"),
        "mission_run_id": queue_item.get("mission_run_id"),
        "department_id": queue_item.get("department_id"),
        "department_display_name": queue_item.get("department_display_name"),
        "task_id": queue_item.get("task_id"),
        "title": queue_item.get("title"),
        "task_type": queue_item.get("task_type"),
        "department_capability": queue_item.get("capability"),
        "gateway_tool_name": gateway_result.get("gateway_tool_name"),
        "local_tool_id": gateway_result.get("local_tool_id"),
        "tool_mode": evaluation.get("tool_mode"),
        "permission": queue_item.get("permission"),
        "approval_required": queue_item.get("approval_required"),
        "credential_required": queue_item.get("credential_required"),
        "live_external_side_effect": queue_item.get("live_external_side_effect"),
        "artifact_type": queue_item.get("artifact_type"),
        "gateway_allowed": evaluation.get("allowed") is True,
        "gateway_state": evaluation.get("gateway_state"),
        "gateway_reasons": reasons,
        "payload_hash": gateway_result.get("payload_hash"),
        "tool_call_hash": evaluation.get("tool_call_hash"),
        "status": status,
        "execution_allowed": status in {"ready", "staged"},
        "live_execution_allowed": False,
        "observation_hash": None,
        "artifact_hash": None,
        "receipt_hash": None,
        "tool_execution_item_hash": "",
    }

    item["tool_execution_item_hash"] = stable_hash(
        {k: v for k, v in item.items() if k != "tool_execution_item_hash"}
    )
    return item


def build_pilot_tool_execution_queue(
    *,
    user_goal: str,
    business_id: str,
    mission_id: str,
    mission_run_id: str,
    department_queue: dict[str, Any] | None = None,
    include_blocked_live_actions: bool = False,
    evaluation_time: int = 0,
    caller: str = "aion_pilot",
) -> dict[str, Any]:
    queue = department_queue or build_department_execution_queue(
        user_goal=user_goal,
        business_id=business_id,
        mission_id=mission_id,
        mission_run_id=mission_run_id,
    )

    if include_blocked_live_actions:
        queue = add_blocked_live_action_cards(queue=queue)

    tool_items = [
        create_tool_execution_item(
            queue_item=item,
            evaluation_time=evaluation_time,
            caller=caller,
        )
        for item in queue.get("queue_items", [])
    ]

    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in tool_items:
        department_id = str(item.get("department_id") or "unknown")
        grouped.setdefault(department_id, []).append(item)

    result = {
        "schema_version": "aion.pilot_tool_execution_queue.v0",
        "business_id": str(business_id or ""),
        "mission_id": str(mission_id or ""),
        "mission_run_id": str(mission_run_id or ""),
        "user_goal": str(user_goal or ""),
        "primary_department": queue.get("primary_department"),
        "supporting_departments": list(queue.get("supporting_departments") or []),
        "tool_execution_items": tool_items,
        "department_tool_queues": grouped,
        "ready_count": sum(1 for item in tool_items if item["status"] == "ready"),
        "staged_count": sum(1 for item in tool_items if item["status"] == "staged"),
        "waiting_approval_count": sum(1 for item in tool_items if item["status"] == "waiting_approval"),
        "blocked_count": sum(1 for item in tool_items if item["status"] == "blocked"),
        "live_execution_allowed": False,
        "raw_model_tool_access_allowed": False,
        "tool_queue_hash": "",
    }

    result["tool_queue_hash"] = stable_hash({k: v for k, v in result.items() if k != "tool_queue_hash"})
    return result


def next_runnable_tool_item(queue: dict[str, Any]) -> dict[str, Any] | None:
    for item in queue.get("tool_execution_items", []):
        if item.get("status") == "ready" and item.get("execution_allowed") is True:
            return item
    for item in queue.get("tool_execution_items", []):
        if item.get("status") == "staged" and item.get("execution_allowed") is True:
            return item
    return None


def summarize_tool_execution_queue(queue: dict[str, Any]) -> dict[str, Any]:
    summary = {
        "schema_version": "aion.pilot_tool_execution_queue_summary.v0",
        "business_id": queue.get("business_id"),
        "mission_id": queue.get("mission_id"),
        "mission_run_id": queue.get("mission_run_id"),
        "primary_department": queue.get("primary_department"),
        "ready_count": queue.get("ready_count", 0),
        "staged_count": queue.get("staged_count", 0),
        "waiting_approval_count": queue.get("waiting_approval_count", 0),
        "blocked_count": queue.get("blocked_count", 0),
        "tool_queue_hash": queue.get("tool_queue_hash"),
        "live_execution_allowed": queue.get("live_execution_allowed") is True,
        "raw_model_tool_access_allowed": queue.get("raw_model_tool_access_allowed") is True,
        "summary_hash": "",
    }
    summary["summary_hash"] = stable_hash({k: v for k, v in summary.items() if k != "summary_hash"})
    return summary
