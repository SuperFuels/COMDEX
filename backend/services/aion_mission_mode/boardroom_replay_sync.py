from __future__ import annotations

from hashlib import sha256
import json
from typing import Any


VALID_REPLAY_EVENT_TYPES = {
    "mission_started",
    "plan_matrix_created",
    "autonomous_step_completed",
    "human_approval_required",
    "human_task_required",
    "external_action_staged",
    "external_action_executed",
    "capability_receipt_created",
    "blocked_action_recorded",
    "cache_eviction_recorded",
    "mission_completed",
    "mission_failed",
}

VALID_VISUAL_ANCHOR_TYPES = {
    "boardroom_step_card",
    "approval_card",
    "human_task_card",
    "staged_action_preview",
    "receipt_card",
    "blocked_action_panel",
    "timeline_marker",
    "proof_replay_link",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def create_replay_event(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    event_type: str,
    event_index: int,
    source_hash: str,
    consensus_hash: str,
    payload: dict[str, Any] | None = None,
    visual_anchor_type: str = "timeline_marker",
) -> dict[str, Any]:
    if event_type not in VALID_REPLAY_EVENT_TYPES:
        raise ValueError(f"invalid replay event type: {event_type}")

    if visual_anchor_type not in VALID_VISUAL_ANCHOR_TYPES:
        raise ValueError(f"invalid visual anchor type: {visual_anchor_type}")

    if event_index < 0:
        raise ValueError("event_index must be non-negative")

    for name, value in {
        "source_hash": source_hash,
        "consensus_hash": consensus_hash,
    }.items():
        if not isinstance(value, str) or not value.startswith("sha256:"):
            raise ValueError(f"{name} must be sha256-prefixed")

    event = {
        "schema_version": "aion.boardroom_replay_event.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "event_type": event_type,
        "event_index": event_index,
        "source_hash": source_hash,
        "consensus_hash": consensus_hash,
        "visual_anchor_type": visual_anchor_type,
        "payload": payload or {},
        "event_hash": "",
    }
    event["event_hash"] = _hash({k: v for k, v in event.items() if k != "event_hash"})
    return event


def compile_replay_timeline(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    ordered = sorted(events, key=lambda event: (event["event_index"], event["event_hash"]))

    reasons: list[str] = []
    seen_indexes: set[int] = set()
    previous_index = -1

    for event in ordered:
        expected_hash = _hash({k: v for k, v in event.items() if k != "event_hash"})
        if event.get("event_hash") != expected_hash:
            reasons.append(f"event_hash_mismatch:{event.get('event_index')}")

        idx = event["event_index"]
        if idx in seen_indexes:
            reasons.append(f"duplicate_event_index:{idx}")
        seen_indexes.add(idx)

        if idx < previous_index:
            reasons.append("event_order_regression")
        previous_index = idx

        if event["mission_id"] != mission_id:
            reasons.append(f"mission_id_mismatch:{idx}")
        if event["mission_run_id"] != mission_run_id:
            reasons.append(f"mission_run_id_mismatch:{idx}")
        if event["business_id"] != business_id:
            reasons.append(f"business_id_mismatch:{idx}")

    valid = not reasons

    timeline = {
        "schema_version": "aion.boardroom_replay_timeline.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "event_count": len(ordered),
        "event_hashes": [event["event_hash"] for event in ordered],
        "timeline_valid": valid,
        "timeline_state": "boardroom_replay_ready" if valid else "boardroom_replay_blocked",
        "reasons": reasons,
        "timeline_hash": "",
    }
    timeline["timeline_hash"] = _hash({k: v for k, v in timeline.items() if k != "timeline_hash"})
    return timeline


def create_visual_anchor(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    event_hash: str,
    anchor_type: str,
    title: str,
    summary: str,
    visible_state: str,
    evidence_hashes: list[str] | None = None,
) -> dict[str, Any]:
    if anchor_type not in VALID_VISUAL_ANCHOR_TYPES:
        raise ValueError(f"invalid visual anchor type: {anchor_type}")

    if not event_hash.startswith("sha256:"):
        raise ValueError("event_hash must be sha256-prefixed")

    sorted_evidence = sorted(evidence_hashes or [])
    for evidence_hash in sorted_evidence:
        if not evidence_hash.startswith("sha256:"):
            raise ValueError("evidence hashes must be sha256-prefixed")

    anchor = {
        "schema_version": "aion.boardroom_visual_anchor.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "event_hash": event_hash,
        "anchor_type": anchor_type,
        "title": title,
        "summary": summary,
        "visible_state": visible_state,
        "evidence_hashes": sorted_evidence,
        "anchor_hash": "",
    }
    anchor["anchor_hash"] = _hash({k: v for k, v in anchor.items() if k != "anchor_hash"})
    return anchor


def compile_boardroom_replay_packet(
    *,
    timeline: dict[str, Any],
    visual_anchors: list[dict[str, Any]],
    consensus_hash: str,
    proof_hash: str,
) -> dict[str, Any]:
    reasons: list[str] = []

    if not timeline.get("timeline_valid", False):
        reasons.append("timeline_invalid")

    for name, value in {
        "timeline_hash": timeline.get("timeline_hash"),
        "consensus_hash": consensus_hash,
        "proof_hash": proof_hash,
    }.items():
        if not isinstance(value, str) or not value.startswith("sha256:"):
            reasons.append(f"invalid_{name}")

    event_hashes = set(timeline.get("event_hashes", []))
    anchor_hashes: list[str] = []

    for anchor in visual_anchors:
        if anchor.get("event_hash") not in event_hashes:
            reasons.append("anchor_event_not_in_timeline")
        expected_anchor_hash = _hash({k: v for k, v in anchor.items() if k != "anchor_hash"})
        if anchor.get("anchor_hash") != expected_anchor_hash:
            reasons.append("anchor_hash_mismatch")
        anchor_hashes.append(anchor["anchor_hash"])

    allowed = not reasons

    packet = {
        "schema_version": "aion.boardroom_replay_packet.v0",
        "mission_id": timeline.get("mission_id"),
        "mission_run_id": timeline.get("mission_run_id"),
        "business_id": timeline.get("business_id"),
        "timeline_hash": timeline.get("timeline_hash"),
        "consensus_hash": consensus_hash,
        "proof_hash": proof_hash,
        "anchor_count": len(visual_anchors),
        "anchor_hashes": sorted(anchor_hashes),
        "allowed": allowed,
        "packet_state": "boardroom_replay_packet_ready" if allowed else "boardroom_replay_packet_blocked",
        "reasons": reasons,
        "packet_hash": "",
    }
    packet["packet_hash"] = _hash({k: v for k, v in packet.items() if k != "packet_hash"})
    return packet


def create_human_in_loop_marker(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    event_hash: str,
    marker_type: str,
    required_action: str,
    approval_or_task_hash: str,
) -> dict[str, Any]:
    valid_marker_types = {
        "approval_required",
        "human_task_required",
        "human_review_required",
        "blocked_for_safety",
    }

    if marker_type not in valid_marker_types:
        raise ValueError(f"invalid human-in-loop marker type: {marker_type}")

    for name, value in {
        "event_hash": event_hash,
        "approval_or_task_hash": approval_or_task_hash,
    }.items():
        if not isinstance(value, str) or not value.startswith("sha256:"):
            raise ValueError(f"{name} must be sha256-prefixed")

    marker = {
        "schema_version": "aion.human_in_loop_visual_marker.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "event_hash": event_hash,
        "marker_type": marker_type,
        "required_action": required_action,
        "approval_or_task_hash": approval_or_task_hash,
        "marker_hash": "",
    }
    marker["marker_hash"] = _hash({k: v for k, v in marker.items() if k != "marker_hash"})
    return marker
