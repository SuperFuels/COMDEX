"""
AION Phase 20T — Deterministic Mission Diff + Payload Escrow

Contract:
- Generate deterministic human-readable diff between template and proposed mission plan.
- Highlight added external, financial, legal, deployment, and memory steps.
- Create payload escrow records for quote/message/booking/publish drafts.
- Bind approval to escrowed payload hash.
- Edited escrow payload invalidates prior approval.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Any

from backend.services.aion_mission_mode.canonical_payload_hashing import (
    payload_sha256_normalized,
)


RISK_LANES = {
    "external_action",
    "financial_action",
    "legal_action",
    "deployment_action",
    "memory_mutation",
}

ESCROW_PAYLOAD_TYPES = {
    "quote_preview",
    "message_draft",
    "booking_preview",
    "publish_payload",
    "advert_publish_payload",
    "customer_reply_payload",
    "payment_preview",
    "escrow_preview",
}


@dataclass(frozen=True)
class MissionDiffEntry:
    change_type: str
    step_id: str
    action_type: str
    lane: str
    risk_flag: bool
    summary: str


@dataclass(frozen=True)
class PayloadEscrowRecord:
    mission_id: str
    mission_run_id: str
    checkpoint_id: str
    step_id: str
    action_type: str
    payload_type: str
    payload_hash: str
    payload: dict[str, Any]
    escrow_state: str = "pending_approval"
    approval_hash: str | None = None
    schema_version: str = "aion.payload_escrow.v0"
    escrow_hash: str = ""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _step_key(step: dict[str, Any]) -> str:
    return str(step.get("step_id") or step.get("action_type") or step.get("id") or "")


def build_mission_diff(
    *,
    template_steps: list[dict[str, Any]],
    proposed_steps: list[dict[str, Any]],
) -> dict[str, Any]:
    template_by_key = {_step_key(step): step for step in template_steps}
    proposed_by_key = {_step_key(step): step for step in proposed_steps}

    entries: list[dict[str, Any]] = []

    for key in sorted(proposed_by_key):
        proposed = proposed_by_key[key]
        lane = str(proposed.get("lane", ""))
        action_type = str(proposed.get("action_type", key))

        if key not in template_by_key:
            entry = MissionDiffEntry(
                change_type="added_step",
                step_id=key,
                action_type=action_type,
                lane=lane,
                risk_flag=lane in RISK_LANES,
                summary=f"Added step {key} in lane {lane}",
            )
            entries.append(asdict(entry))
            continue

        template = template_by_key[key]
        changed_fields = []
        for field in ("action_type", "lane", "title", "description"):
            if str(template.get(field, "")) != str(proposed.get(field, "")):
                changed_fields.append(field)

        if changed_fields:
            entry = MissionDiffEntry(
                change_type="modified_step",
                step_id=key,
                action_type=action_type,
                lane=lane,
                risk_flag=lane in RISK_LANES or str(template.get("lane", "")) in RISK_LANES,
                summary=f"Modified step {key}: {', '.join(sorted(changed_fields))}",
            )
            entries.append(asdict(entry))

    for key in sorted(template_by_key):
        if key not in proposed_by_key:
            template = template_by_key[key]
            lane = str(template.get("lane", ""))
            entry = MissionDiffEntry(
                change_type="removed_step",
                step_id=key,
                action_type=str(template.get("action_type", key)),
                lane=lane,
                risk_flag=lane in RISK_LANES,
                summary=f"Removed step {key}",
            )
            entries.append(asdict(entry))

    diff = {
        "schema_version": "aion.mission_diff.v0",
        "entries": entries,
        "risk_added": any(e["risk_flag"] for e in entries),
        "diff_hash": "",
    }
    diff["diff_hash"] = _hash({k: v for k, v in diff.items() if k != "diff_hash"})
    return diff


def create_payload_escrow_record(
    *,
    mission_id: str,
    mission_run_id: str,
    checkpoint_id: str,
    step_id: str,
    action_type: str,
    payload_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if payload_type not in ESCROW_PAYLOAD_TYPES:
        raise ValueError(f"unsupported_escrow_payload_type:{payload_type}")

    record = PayloadEscrowRecord(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        checkpoint_id=checkpoint_id,
        step_id=step_id,
        action_type=action_type,
        payload_type=payload_type,
        payload_hash=payload_sha256_normalized(payload),
        payload=payload,
    )
    data = asdict(record)
    data["escrow_hash"] = _hash({k: v for k, v in data.items() if k != "escrow_hash"})
    return data


def bind_approval_to_escrow(
    *,
    escrow_record: dict[str, Any],
    approval_hash: str,
    approved_payload_hash: str,
) -> dict[str, Any]:
    if approved_payload_hash != escrow_record.get("payload_hash"):
        return {
            **escrow_record,
            "escrow_state": "approval_payload_hash_mismatch",
            "approval_hash": approval_hash,
            "approval_bound": False,
            "requires_fresh_approval": True,
        }

    bound = {
        **escrow_record,
        "escrow_state": "approval_bound",
        "approval_hash": approval_hash,
        "approval_bound": True,
        "requires_fresh_approval": False,
    }
    bound["escrow_hash"] = _hash({k: v for k, v in bound.items() if k != "escrow_hash"})
    return bound


def validate_escrow_payload_unchanged(
    *,
    escrow_record: dict[str, Any],
    current_payload: dict[str, Any],
) -> dict[str, Any]:
    current_hash = payload_sha256_normalized(current_payload)
    unchanged = current_hash == escrow_record.get("payload_hash")

    return {
        "escrow_hash": escrow_record.get("escrow_hash"),
        "approved_payload_hash": escrow_record.get("payload_hash"),
        "current_payload_hash": current_hash,
        "payload_unchanged": unchanged,
        "execution_allowed": unchanged and escrow_record.get("escrow_state") == "approval_bound",
        "requires_fresh_approval": not unchanged,
        "reason": "escrow_payload_unchanged" if unchanged else "escrow_payload_changed_requires_fresh_approval",
        "validation_hash": _hash(
            {
                "escrow_hash": escrow_record.get("escrow_hash"),
                "approved_payload_hash": escrow_record.get("payload_hash"),
                "current_payload_hash": current_hash,
                "payload_unchanged": unchanged,
            }
        ),
    }
