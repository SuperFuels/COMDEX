from __future__ import annotations

from hashlib import sha256
import json
from typing import Any


VALID_TIMELINE_EVENT_TYPES = {
    "mission_started",
    "step_started",
    "step_completed",
    "approval_requested",
    "approval_granted",
    "human_task_created",
    "human_task_completed",
    "action_blocked",
    "receipt_emitted",
    "replay_snapshot",
    "ets_preview_emitted",
    "mission_completed",
    "mission_failed",
}

VALID_TIMELINE_STATES = {
    "pending",
    "running",
    "completed",
    "waiting_approval",
    "waiting_human_task",
    "blocked_for_safety",
    "failed",
    "replay_only",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _require_sha256(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        raise ValueError(f"{name} must be sha256-prefixed")


def create_timeline_event(event: dict[str, Any]) -> dict[str, Any]:
    event_type = event.get("event_type")
    if event_type not in VALID_TIMELINE_EVENT_TYPES:
        raise ValueError(f"invalid timeline event type: {event_type}")

    sequence_number = event.get("sequence_number")
    if not isinstance(sequence_number, int) or sequence_number < 0:
        raise ValueError("sequence_number must be a non-negative integer")

    source_hash = event.get("source_hash", "sha256:none")
    _require_sha256("source_hash", source_hash)

    timeline_event = {
        "schema_version": "aion.boardroom.timeline_event.v0",
        "mission_id": event["mission_id"],
        "mission_run_id": event["mission_run_id"],
        "business_id": event["business_id"],
        "sequence_number": sequence_number,
        "event_type": event_type,
        "step_id": event.get("step_id", "none"),
        "title": event.get("title", ""),
        "summary": event.get("summary", ""),
        "state_after": event.get("state_after", "running"),
        "source_hash": source_hash,
        "receipt_hash": event.get("receipt_hash", "none"),
        "approval_hash": event.get("approval_hash", "none"),
        "human_task_hash": event.get("human_task_hash", "none"),
        "blocked_action_hash": event.get("blocked_action_hash", "none"),
        "event_hash": "",
    }

    if timeline_event["state_after"] not in VALID_TIMELINE_STATES:
        raise ValueError(f"invalid state_after: {timeline_event['state_after']}")

    for key in ["receipt_hash", "approval_hash", "human_task_hash", "blocked_action_hash"]:
        if timeline_event[key] != "none":
            _require_sha256(key, timeline_event[key])

    timeline_event["event_hash"] = _hash(
        {k: v for k, v in timeline_event.items() if k != "event_hash"}
    )
    return timeline_event


def compile_live_timeline(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    panel_hash: str,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    _require_sha256("panel_hash", panel_hash)

    event_views = [create_timeline_event(event) for event in events]
    event_views = sorted(event_views, key=lambda e: (e["sequence_number"], e["event_hash"]))

    seen_sequences: set[int] = set()
    for event in event_views:
        seq = event["sequence_number"]
        if seq in seen_sequences:
            raise ValueError(f"duplicate timeline sequence_number: {seq}")
        seen_sequences.add(seq)

    completed_steps = sum(1 for e in event_views if e["event_type"] == "step_completed")
    approval_waits = sum(1 for e in event_views if e["event_type"] == "approval_requested")
    human_task_waits = sum(1 for e in event_views if e["event_type"] == "human_task_created")
    blocked_actions = sum(1 for e in event_views if e["event_type"] == "action_blocked")
    receipt_count = sum(1 for e in event_views if e["event_type"] == "receipt_emitted")

    latest_state = event_views[-1]["state_after"] if event_views else "pending"

    timeline = {
        "schema_version": "aion.boardroom.live_timeline.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "panel_hash": panel_hash,
        "event_count": len(event_views),
        "completed_steps": completed_steps,
        "approval_waits": approval_waits,
        "human_task_waits": human_task_waits,
        "blocked_actions": blocked_actions,
        "receipt_count": receipt_count,
        "latest_state": latest_state,
        "timeline_events": event_views,
        "timeline_executes_tools": False,
        "timeline_mutates_provider_state": False,
        "timeline_hash": "",
    }

    timeline["timeline_hash"] = _hash({k: v for k, v in timeline.items() if k != "timeline_hash"})
    return timeline


def assert_live_timeline_safety(timeline: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []

    expected_hash = _hash({k: v for k, v in timeline.items() if k != "timeline_hash"})
    if timeline.get("timeline_hash") != expected_hash:
        reasons.append("timeline_hash_mismatch")

    if timeline.get("timeline_executes_tools") is not False:
        reasons.append("timeline_must_not_execute_tools")

    if timeline.get("timeline_mutates_provider_state") is not False:
        reasons.append("timeline_must_not_mutate_provider_state")

    allowed = not reasons

    result = {
        "schema_version": "aion.boardroom.timeline_safety.v0",
        "mission_id": timeline.get("mission_id"),
        "mission_run_id": timeline.get("mission_run_id"),
        "business_id": timeline.get("business_id"),
        "allowed": allowed,
        "safety_state": "timeline_safe" if allowed else "timeline_blocked",
        "reasons": reasons,
        "timeline_hash": timeline.get("timeline_hash"),
        "safety_hash": "",
    }

    result["safety_hash"] = _hash({k: v for k, v in result.items() if k != "safety_hash"})
    return result
