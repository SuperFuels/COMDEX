"""
AION Phase 20Y — Canonical Payload Hashing

Contract:
- Checkpoint payload JSON is canonicalised with sorted keys.
- Non-semantic whitespace does not affect payload hash.
- Payload hash is SHA256 over canonical JSON.
- Payload hash is recalculated immediately before execution.
- Edited payloads invalidate approval.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Any


@dataclass(frozen=True)
class PayloadHashRecord:
    mission_id: str
    mission_run_id: str
    checkpoint_id: str
    step_id: str
    action_type: str
    payload_hash: str
    canonical_payload: str
    hash_algorithm: str = "sha256"
    schema_version: str = "aion.payload_hash.v0"


@dataclass(frozen=True)
class PayloadExecutionValidation:
    mission_id: str
    mission_run_id: str
    checkpoint_id: str
    step_id: str
    action_type: str
    approved_payload_hash: str
    current_payload_hash: str
    payload_unchanged: bool
    execution_allowed: bool
    reason: str
    validation_hash: str = ""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def payload_sha256(payload: dict[str, Any]) -> str:
    return "sha256:" + sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def create_payload_hash_record(
    *,
    mission_id: str,
    mission_run_id: str,
    checkpoint_id: str,
    step_id: str,
    action_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    canonical = canonical_json(payload)
    record = PayloadHashRecord(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        checkpoint_id=checkpoint_id,
        step_id=step_id,
        action_type=action_type,
        payload_hash="sha256:" + sha256(canonical.encode("utf-8")).hexdigest(),
        canonical_payload=canonical,
    )
    return asdict(record)


def validate_payload_before_execution(
    *,
    mission_id: str,
    mission_run_id: str,
    checkpoint_id: str,
    step_id: str,
    action_type: str,
    approved_payload_hash: str,
    current_payload: dict[str, Any],
) -> dict[str, Any]:
    current_hash = payload_sha256(current_payload)
    unchanged = approved_payload_hash == current_hash

    result = PayloadExecutionValidation(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        checkpoint_id=checkpoint_id,
        step_id=step_id,
        action_type=action_type,
        approved_payload_hash=approved_payload_hash,
        current_payload_hash=current_hash,
        payload_unchanged=unchanged,
        execution_allowed=unchanged,
        reason="payload_hash_match" if unchanged else "payload_hash_mismatch_requires_fresh_approval",
    )

    data = asdict(result)
    data["validation_hash"] = payload_sha256({k: v for k, v in data.items() if k != "validation_hash"})
    return data


def approval_payload_hash_matches(
    *,
    approval: dict[str, Any],
    current_payload: dict[str, Any],
) -> bool:
    return approval.get("payload_hash") == payload_sha256(current_payload)


def invalidate_approval_if_payload_changed(
    *,
    approval: dict[str, Any],
    current_payload: dict[str, Any],
) -> dict[str, Any]:
    current_hash = payload_sha256(current_payload)
    approved_hash = approval.get("payload_hash")

    if approved_hash == current_hash:
        return {
            "approval_valid": True,
            "approved_payload_hash": approved_hash,
            "current_payload_hash": current_hash,
            "reason": "payload_unchanged",
            "requires_fresh_approval": False,
        }

    return {
        "approval_valid": False,
        "approved_payload_hash": approved_hash,
        "current_payload_hash": current_hash,
        "reason": "payload_changed_after_approval",
        "requires_fresh_approval": True,
    }
