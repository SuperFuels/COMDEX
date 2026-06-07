from __future__ import annotations

from hashlib import sha256
import json
from typing import Any


VALID_STEP_STATES = {
    "pending",
    "running",
    "completed",
    "waiting_approval",
    "waiting_human_task",
    "blocked",
    "skipped",
    "failed",
}

VALID_PANEL_STATES = {
    "mission_ready",
    "mission_running",
    "waiting_approval",
    "waiting_human_task",
    "blocked_for_safety",
    "completed",
    "replay_only",
}

REQUIRED_VISIBLE_MESSAGE = "AION stopped itself before doing anything risky"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _require_sha256(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        raise ValueError(f"{name} must be sha256-prefixed")


def create_mission_step_view(step: dict[str, Any]) -> dict[str, Any]:
    step_id = step.get("step_id")
    title = step.get("title")
    state = step.get("state", "pending")

    if not step_id or not title:
        raise ValueError("step requires step_id and title")
    if state not in VALID_STEP_STATES:
        raise ValueError(f"invalid step state: {state}")

    view = {
        "schema_version": "aion.boardroom.step_view.v0",
        "step_id": step_id,
        "title": title,
        "description": step.get("description", ""),
        "state": state,
        "lane": step.get("lane", "unknown"),
        "risk_level": step.get("risk_level", "unknown"),
        "control_mode": step.get("control_mode", "autonomous"),
        "requires_approval": bool(step.get("requires_approval", False)),
        "requires_human_task": bool(step.get("requires_human_task", False)),
        "blocked_reason": step.get("blocked_reason", "none"),
        "receipt_hash": step.get("receipt_hash", "none"),
        "step_view_hash": "",
    }

    if view["receipt_hash"] != "none":
        _require_sha256("receipt_hash", view["receipt_hash"])

    view["step_view_hash"] = _hash({k: v for k, v in view.items() if k != "step_view_hash"})
    return view


def create_boardroom_control_panel(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    panel_state: str,
    current_step_id: str | None,
    next_checkpoint_id: str | None,
    plan_approval_matrix_hash: str,
    mission_trace_hash: str,
    replay_hash: str,
    ets_preview_hash: str,
    demo_summary_hash: str,
    steps: list[dict[str, Any]],
    blocked_actions: list[dict[str, Any]] | None = None,
    human_tasks: list[dict[str, Any]] | None = None,
    approval_gates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if panel_state not in VALID_PANEL_STATES:
        raise ValueError(f"invalid panel state: {panel_state}")

    for name, value in {
        "plan_approval_matrix_hash": plan_approval_matrix_hash,
        "mission_trace_hash": mission_trace_hash,
        "replay_hash": replay_hash,
        "ets_preview_hash": ets_preview_hash,
        "demo_summary_hash": demo_summary_hash,
    }.items():
        _require_sha256(name, value)

    step_views = [create_mission_step_view(step) for step in steps]

    step_ids = {step["step_id"] for step in step_views}
    if current_step_id is not None and current_step_id not in step_ids:
        raise ValueError("current_step_id is not present in steps")
    if next_checkpoint_id is not None and next_checkpoint_id not in step_ids:
        raise ValueError("next_checkpoint_id is not present in steps")

    blocked_actions = blocked_actions or []
    human_tasks = human_tasks or []
    approval_gates = approval_gates or []

    completed_count = sum(1 for step in step_views if step["state"] == "completed")
    blocked_count = sum(1 for step in step_views if step["state"] == "blocked")
    waiting_approval_count = sum(1 for step in step_views if step["state"] == "waiting_approval")
    waiting_human_task_count = sum(1 for step in step_views if step["state"] == "waiting_human_task")

    panel = {
        "schema_version": "aion.boardroom.control_panel.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "panel_state": panel_state,
        "current_step_id": current_step_id or "none",
        "next_checkpoint_id": next_checkpoint_id or "none",
        "required_visible_message": REQUIRED_VISIBLE_MESSAGE,
        "plan_approval_matrix_hash": plan_approval_matrix_hash,
        "mission_trace_hash": mission_trace_hash,
        "replay_hash": replay_hash,
        "ets_preview_hash": ets_preview_hash,
        "demo_summary_hash": demo_summary_hash,
        "step_count": len(step_views),
        "completed_count": completed_count,
        "blocked_count": blocked_count,
        "waiting_approval_count": waiting_approval_count,
        "waiting_human_task_count": waiting_human_task_count,
        "step_views": step_views,
        "blocked_actions": sorted(blocked_actions, key=lambda item: item.get("action_type", "")),
        "human_tasks": sorted(human_tasks, key=lambda item: item.get("task_id", "")),
        "approval_gates": sorted(approval_gates, key=lambda item: item.get("approval_id", "")),
        "live_action_buttons_enabled": False,
        "replay_mode_executes_tools": False,
        "panel_hash": "",
    }

    panel["panel_hash"] = _hash({k: v for k, v in panel.items() if k != "panel_hash"})
    return panel


def assert_boardroom_panel_safety(panel: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []

    expected_hash = _hash({k: v for k, v in panel.items() if k != "panel_hash"})
    if panel.get("panel_hash") != expected_hash:
        reasons.append("panel_hash_mismatch")

    if panel.get("required_visible_message") != REQUIRED_VISIBLE_MESSAGE:
        reasons.append("required_visible_message_missing")

    if panel.get("live_action_buttons_enabled") is not False:
        reasons.append("live_action_buttons_must_be_disabled")

    if panel.get("replay_mode_executes_tools") is not False:
        reasons.append("replay_must_not_execute_tools")

    if panel.get("panel_state") == "replay_only" and panel.get("live_action_buttons_enabled") is not False:
        reasons.append("replay_mode_live_action_button_violation")

    allowed = not reasons

    result = {
        "schema_version": "aion.boardroom.panel_safety.v0",
        "mission_id": panel.get("mission_id"),
        "mission_run_id": panel.get("mission_run_id"),
        "business_id": panel.get("business_id"),
        "allowed": allowed,
        "safety_state": "boardroom_panel_safe" if allowed else "boardroom_panel_blocked",
        "reasons": reasons,
        "panel_hash": panel.get("panel_hash"),
        "safety_hash": "",
    }
    result["safety_hash"] = _hash({k: v for k, v in result.items() if k != "safety_hash"})
    return result


def create_boardroom_replay_projection(panel: dict[str, Any]) -> dict[str, Any]:
    safety = assert_boardroom_panel_safety(panel)
    if not safety["allowed"]:
        raise ValueError("cannot create replay projection for unsafe panel")

    projection = {
        "schema_version": "aion.boardroom.replay_projection.v0",
        "mission_id": panel["mission_id"],
        "mission_run_id": panel["mission_run_id"],
        "business_id": panel["business_id"],
        "panel_hash": panel["panel_hash"],
        "mission_trace_hash": panel["mission_trace_hash"],
        "replay_hash": panel["replay_hash"],
        "ets_preview_hash": panel["ets_preview_hash"],
        "demo_summary_hash": panel["demo_summary_hash"],
        "projection_state": "replay_projection_ready",
        "read_only": True,
        "tools_executable": False,
        "live_provider_mutation_allowed": False,
        "projection_hash": "",
    }
    projection["projection_hash"] = _hash({k: v for k, v in projection.items() if k != "projection_hash"})
    return projection
