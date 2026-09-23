"""
AION Phase 20E — Mission Runtime State Machine v0

Contract:
- Mounts only Kernel Guard approved safe autonomous batches.
- Runs preview/internal safe steps only.
- Pauses at checkpoint/risk boundary.
- Enforces runtime, tool-call, and cost limits.
- Emits deterministic runtime trace and state hash.
- No live external writes.
- No email/WhatsApp sends.
- No payment, booking, escrow, deployment, dispatch, reputation mutation, or chain write.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from hashlib import sha256
import json
from typing import Any

from backend.services.aion_mission_mode.autonomy_lane_classifier import (
    classify_mission_steps,
    verify_runtime_queue_hash,
)
from backend.services.aion_mission_mode.kernel_guard import inspect_kernel_batch


RUNTIME_STATES = {
    "created",
    "planning",
    "waiting_mission_approval",
    "ready_for_runtime",
    "running_autonomous_steps",
    "paused_at_checkpoint",
    "waiting_human_review",
    "blocked",
    "completed",
    "failed",
    "expired",
    "cancelled",
}


@dataclass(frozen=True)
class MissionRuntimeLimits:
    max_runtime_seconds: int = 1800
    max_tool_calls: int = 50
    max_cost: float = 0.0


@dataclass
class MissionRuntimeState:
    mission_id: str
    mission_run_id: str
    status: str = "created"
    current_step_index: int = 0
    completed_step_ids: list[str] = field(default_factory=list)
    paused_step_id: str | None = None
    blocked_reason: str | None = None
    tool_calls_used: int = 0
    cost_used: float = 0.0
    trace_events: list[dict[str, Any]] = field(default_factory=list)
    state_hash: str = ""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _runtime_event(event_type: str, **payload: Any) -> dict[str, Any]:
    return {
        "event_type": event_type,
        **payload,
    }


def _state_hash(state: MissionRuntimeState) -> str:
    payload = asdict(state)
    payload.pop("state_hash", None)
    return "sha256:" + _hash(payload)


def _step_id(step: dict[str, Any], index: int) -> str:
    return str(step.get("step_id") or f"step_{index:02d}_{step.get('action_type', 'unknown')}")


def _validate_limits(
    *,
    state: MissionRuntimeState,
    limits: MissionRuntimeLimits,
    step_cost: float = 0.0,
) -> str | None:
    if state.tool_calls_used >= limits.max_tool_calls:
        return "max_tool_calls_exceeded"
    if state.cost_used + step_cost > limits.max_cost:
        return "max_cost_exceeded"
    return None


def mount_mission_runtime(
    *,
    mission_id: str,
    mission_run_id: str,
    steps: list[dict[str, Any]],
    limits: MissionRuntimeLimits | None = None,
) -> dict[str, Any]:
    limits = limits or MissionRuntimeLimits()

    state = MissionRuntimeState(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        status="created",
    )

    classifier_result = classify_mission_steps(steps)
    verify = verify_runtime_queue_hash(
        classifier_result=classifier_result,
        runtime_classifications=classifier_result["classifications"],
    )

    if not verify["runtime_mount_allowed"]:
        state.status = "blocked"
        state.blocked_reason = str(verify.get("trace_event") or "classifier_runtime_mount_refused")
        state.trace_events.append(_runtime_event(
            "runtime_mount_blocked_by_classifier",
            reason=state.blocked_reason,
            classifier_run_hash=classifier_result.get("classifier_run_hash"),
        ))
        state.state_hash = _state_hash(state)
        return {
            "mounted": False,
            "state": asdict(state),
            "classifier_result": classifier_result,
            "kernel_guard_result": None,
        }

    kernel_guard_result = inspect_kernel_batch(steps)
    if not kernel_guard_result["runtime_mount_allowed"]:
        state.status = "waiting_human_review"
        state.blocked_reason = "kernel_guard_runtime_mount_refused"
        state.trace_events.append(_runtime_event(
            "runtime_mount_blocked_by_kernel_guard",
            reason=state.blocked_reason,
            kernel_guard_run_hash=kernel_guard_result.get("kernel_guard_run_hash"),
            boardroom_alerts=kernel_guard_result.get("boardroom_alerts", []),
        ))
        state.state_hash = _state_hash(state)
        return {
            "mounted": False,
            "state": asdict(state),
            "classifier_result": classifier_result,
            "kernel_guard_result": kernel_guard_result,
        }

    state.status = "ready_for_runtime"
    state.trace_events.append(_runtime_event(
        "runtime_mounted",
        classifier_run_hash=classifier_result.get("classifier_run_hash"),
        kernel_guard_run_hash=kernel_guard_result.get("kernel_guard_run_hash"),
        step_count=len(steps),
    ))
    state.state_hash = _state_hash(state)

    return {
        "mounted": True,
        "state": asdict(state),
        "classifier_result": classifier_result,
        "kernel_guard_result": kernel_guard_result,
    }


def run_mission_runtime_preview(
    *,
    mission_id: str,
    mission_run_id: str,
    steps: list[dict[str, Any]],
    limits: MissionRuntimeLimits | None = None,
) -> dict[str, Any]:
    limits = limits or MissionRuntimeLimits()

    mount = mount_mission_runtime(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        steps=steps,
        limits=limits,
    )

    state_data = mount["state"]
    state = MissionRuntimeState(
        mission_id=state_data["mission_id"],
        mission_run_id=state_data["mission_run_id"],
        status=state_data["status"],
        current_step_index=state_data["current_step_index"],
        completed_step_ids=list(state_data["completed_step_ids"]),
        paused_step_id=state_data["paused_step_id"],
        blocked_reason=state_data["blocked_reason"],
        tool_calls_used=state_data["tool_calls_used"],
        cost_used=state_data["cost_used"],
        trace_events=list(state_data["trace_events"]),
        state_hash=state_data["state_hash"],
    )

    if not mount["mounted"]:
        return {
            "completed": False,
            "state": asdict(state),
            "mount": mount,
            "live_side_effects_enabled": False,
        }

    state.status = "running_autonomous_steps"

    for index, step in enumerate(steps):
        state.current_step_index = index
        sid = _step_id(step, index)

        limit_reason = _validate_limits(state=state, limits=limits)
        if limit_reason:
            state.status = "blocked"
            state.paused_step_id = sid
            state.blocked_reason = limit_reason
            state.trace_events.append(_runtime_event("runtime_limit_blocked", step_id=sid, reason=limit_reason))
            state.state_hash = _state_hash(state)
            return {
                "completed": False,
                "state": asdict(state),
                "mount": mount,
                "live_side_effects_enabled": False,
            }

        kernel_decision = inspect_kernel_batch([step])["decisions"][0]
        if not kernel_decision["runtime_mount_allowed"]:
            state.status = "paused_at_checkpoint"
            state.paused_step_id = sid
            state.blocked_reason = kernel_decision["reason"]
            state.trace_events.append(_runtime_event(
                "runtime_paused_at_checkpoint",
                step_id=sid,
                action_type=kernel_decision["action_type"],
                reason=kernel_decision["reason"],
            ))
            state.state_hash = _state_hash(state)
            return {
                "completed": False,
                "state": asdict(state),
                "mount": mount,
                "live_side_effects_enabled": False,
            }

        state.tool_calls_used += 1
        state.completed_step_ids.append(sid)
        state.trace_events.append(_runtime_event(
            "runtime_safe_step_completed",
            step_id=sid,
            action_type=kernel_decision["action_type"],
            guard_hash=kernel_decision["guard_hash"],
        ))

    state.status = "completed"
    state.current_step_index = len(steps)
    state.trace_events.append(_runtime_event(
        "runtime_completed_preview",
        completed_count=len(state.completed_step_ids),
    ))
    state.state_hash = _state_hash(state)

    return {
        "completed": True,
        "state": asdict(state),
        "mount": mount,
        "live_side_effects_enabled": False,
    }
