"""
AION Phase 20Z — AION Pilot Native Runtime + Process Isolation

Contract:
- AION Pilot is a native AION runtime capability.
- Pilot is not a separate app, not an OpenClaw clone, and not UI automation.
- Pilot does not click, type, scrape, or navigate the UI like a user.
- Pilot runs through internal AION services and governed Mission Contracts.
- Runtime work is async/bounded and exposes kill-switch semantics.
- Kill-switch preserves trace, receipts, state hash, and partial outputs.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from hashlib import sha256
import json
from typing import Any


PILOT_EXECUTOR_NAME = "AION Pilot"
NATIVE_RUNTIME_OWNER = "aion_core"

FORBIDDEN_UI_AUTOMATION_METHODS = {
    "click_ui",
    "type_into_ui",
    "scrape_ui",
    "navigate_ui",
    "cursor_move",
    "browser_ui_drive",
    "desktop_automation",
    "screen_scrape",
}

ALLOWED_NATIVE_SURFACES = {
    "aion_terminal",
    "command_bar",
    "boardroom_mission_control",
    "workflow_canvas_preview",
}

ALLOWED_INTERNAL_SERVICE_ROUTES = {
    "mission_contract",
    "mission_template",
    "mission_planner",
    "autonomy_lane_classifier",
    "kernel_guard",
    "mission_runtime",
    "business_container_artifacts",
    "proof_replay",
    "ets_preview",
}


@dataclass(frozen=True)
class PilotNativeRuntimePolicy:
    executor_name: str = PILOT_EXECUTOR_NAME
    native_runtime_owner: str = NATIVE_RUNTIME_OWNER
    is_native_aion_capability: bool = True
    separate_app: bool = False
    openclaw_clone: bool = False
    ui_automation_allowed: bool = False
    runs_async_outside_primary_ui_thread: bool = True
    bounded_worker_required: bool = True
    throttled_io_required: bool = True
    kill_switch_required: bool = True
    preserve_trace_on_kill: bool = True
    preserve_receipts_on_kill: bool = True
    preserve_partial_outputs_on_kill: bool = True


@dataclass(frozen=True)
class PilotInvocation:
    mission_id: str
    mission_run_id: str
    started_from_surface: str
    supervised_from_surface: str
    workflow_canvas_visible: bool = True


@dataclass
class PilotWorkerState:
    mission_id: str
    mission_run_id: str
    worker_id: str
    status: str = "created"
    kill_switch_armed: bool = False
    cpu_limit_label: str = "bounded"
    memory_limit_label: str = "bounded"
    io_channel: str = "mission_scoped_throttled"
    trace_events: list[dict[str, Any]] = field(default_factory=list)
    partial_outputs: list[dict[str, Any]] = field(default_factory=list)
    receipt_refs: list[str] = field(default_factory=list)
    state_hash: str = ""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _state_hash(state: PilotWorkerState) -> str:
    payload = asdict(state)
    payload.pop("state_hash", None)
    return "sha256:" + _hash(payload)


def validate_pilot_native_policy(policy: PilotNativeRuntimePolicy | None = None) -> bool:
    policy = policy or PilotNativeRuntimePolicy()

    return all(
        [
            policy.executor_name == PILOT_EXECUTOR_NAME,
            policy.native_runtime_owner == NATIVE_RUNTIME_OWNER,
            policy.is_native_aion_capability is True,
            policy.separate_app is False,
            policy.openclaw_clone is False,
            policy.ui_automation_allowed is False,
            policy.runs_async_outside_primary_ui_thread is True,
            policy.bounded_worker_required is True,
            policy.throttled_io_required is True,
            policy.kill_switch_required is True,
        ]
    )


def validate_invocation_surface(invocation: PilotInvocation) -> bool:
    return (
        invocation.started_from_surface in {"aion_terminal", "command_bar"}
        and invocation.supervised_from_surface == "boardroom_mission_control"
        and invocation.workflow_canvas_visible is True
    )


def reject_ui_automation_action(action_type: str) -> dict[str, Any]:
    normalised = str(action_type or "").strip().lower().replace("-", "_").replace(" ", "_")

    if normalised in FORBIDDEN_UI_AUTOMATION_METHODS:
        return {
            "allowed": False,
            "reason": "pilot_ui_automation_forbidden",
            "action_type": normalised,
        }

    return {
        "allowed": True,
        "reason": "not_ui_automation",
        "action_type": normalised,
    }


def validate_internal_service_route(route: str) -> bool:
    return str(route or "") in ALLOWED_INTERNAL_SERVICE_ROUTES


def create_pilot_worker_state(
    *,
    mission_id: str,
    mission_run_id: str,
    worker_id: str,
) -> dict[str, Any]:
    state = PilotWorkerState(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        worker_id=worker_id,
        status="created",
    )
    state.trace_events.append(
        {
            "event_type": "pilot_worker_created",
            "runtime_owner": NATIVE_RUNTIME_OWNER,
            "executor_name": PILOT_EXECUTOR_NAME,
        }
    )
    state.state_hash = _state_hash(state)
    return asdict(state)


def start_pilot_worker(state_data: dict[str, Any]) -> dict[str, Any]:
    state = PilotWorkerState(**{k: v for k, v in state_data.items() if k in PilotWorkerState.__dataclass_fields__})
    state.status = "running"
    state.trace_events.append(
        {
            "event_type": "pilot_worker_started",
            "async_outside_primary_ui_thread": True,
            "io_channel": state.io_channel,
        }
    )
    state.state_hash = _state_hash(state)
    return asdict(state)


def kill_pilot_worker(
    state_data: dict[str, Any],
    *,
    reason: str = "operator_kill_switch",
) -> dict[str, Any]:
    state = PilotWorkerState(**{k: v for k, v in state_data.items() if k in PilotWorkerState.__dataclass_fields__})
    state.status = "killed"
    state.trace_events.append(
        {
            "event_type": "pilot_worker_killed",
            "reason": reason,
            "preserved_trace": True,
            "preserved_receipts": True,
            "preserved_partial_outputs": True,
        }
    )
    state.state_hash = _state_hash(state)
    return asdict(state)


def boardroom_state_sync_hash(
    *,
    runtime_state_hash: str,
    worker_state_hash: str,
    mission_id: str,
    mission_run_id: str,
) -> str:
    return "sha256:" + _hash(
        {
            "mission_id": mission_id,
            "mission_run_id": mission_run_id,
            "runtime_state_hash": runtime_state_hash,
            "worker_state_hash": worker_state_hash,
        }
    )


def validate_boardroom_state_sync(
    *,
    expected_sync_hash: str,
    runtime_state_hash: str,
    worker_state_hash: str,
    mission_id: str,
    mission_run_id: str,
) -> bool:
    return expected_sync_hash == boardroom_state_sync_hash(
        runtime_state_hash=runtime_state_hash,
        worker_state_hash=worker_state_hash,
        mission_id=mission_id,
        mission_run_id=mission_run_id,
    )


class PilotWorkerPreemptionError(RuntimeError):
    """Raised when the Pilot worker is interrupted before/after a micro-step."""


def preemption_checkpoint(
    state_data: dict[str, Any],
    *,
    checkpoint_id: str,
    phase: str,
) -> dict[str, Any]:
    """
    Atomic pre-emption checkpoint.

    The worker loop must call this before and after every internal micro-step.
    If kill_switch_armed is False, execution is interrupted before any further
    tool or service route can run.
    """
    state = PilotWorkerState(**{k: v for k, v in state_data.items() if k in PilotWorkerState.__dataclass_fields__})

    if state.kill_switch_armed is True:
        state.status = "killed"
        state.trace_events.append(
            {
                "event_type": "pilot_worker_preempted",
                "checkpoint_id": checkpoint_id,
                "phase": phase,
                "reason": "kill_switch_armed",
                "no_further_tool_execution": True,
                "preserved_trace": True,
                "preserved_receipts": True,
                "preserved_partial_outputs": True,
            }
        )
        state.state_hash = _state_hash(state)
        raise PilotWorkerPreemptionError(_canonical_json(asdict(state)))

    state.trace_events.append(
        {
            "event_type": "pilot_worker_preemption_checkpoint_passed",
            "checkpoint_id": checkpoint_id,
            "phase": phase,
        }
    )
    state.state_hash = _state_hash(state)
    return asdict(state)


def request_worker_stop(state_data: dict[str, Any], *, reason: str = "operator_stop_requested") -> dict[str, Any]:
    """
    Cooperative stop request.

    This flips kill_switch_armed to True. The next preemption checkpoint must
    halt execution before another internal tool block starts.
    """
    state = PilotWorkerState(**{k: v for k, v in state_data.items() if k in PilotWorkerState.__dataclass_fields__})
    state.kill_switch_armed = True
    state.trace_events.append(
        {
            "event_type": "pilot_worker_stop_requested",
            "reason": reason,
            "next_preemption_checkpoint_must_halt": True,
        }
    )
    state.state_hash = _state_hash(state)
    return asdict(state)


def boardroom_divergence_action(
    *,
    expected_sync_hash: str,
    runtime_state_hash: str,
    worker_state_hash: str,
    mission_id: str,
    mission_run_id: str,
) -> dict[str, Any]:
    calculated = boardroom_state_sync_hash(
        runtime_state_hash=runtime_state_hash,
        worker_state_hash=worker_state_hash,
        mission_id=mission_id,
        mission_run_id=mission_run_id,
    )

    if calculated != expected_sync_hash:
        return {
            "boardroom_trustworthy": False,
            "controls_frozen": True,
            "status_monitors_greyed": True,
            "critical_error": "boardroom_state_desynchronization",
            "expected_sync_hash": expected_sync_hash,
            "calculated_sync_hash": calculated,
            "mission_id": mission_id,
            "mission_run_id": mission_run_id,
        }

    return {
        "boardroom_trustworthy": True,
        "controls_frozen": False,
        "status_monitors_greyed": False,
        "critical_error": None,
        "expected_sync_hash": expected_sync_hash,
        "calculated_sync_hash": calculated,
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
    }
