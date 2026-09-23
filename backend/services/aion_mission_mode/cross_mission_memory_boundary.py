"""
AION Phase 20S — Cross-Mission Memory Boundary

Contract:
- Mission data does not leak into later missions by default.
- data_retention_policy is respected.
- Memory promotion requires a proposal and approval.
- Mission memory scope is explicit.
- Accidental leakage is blocked, not only malicious leakage.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Any, Literal


MissionMemoryScope = Literal[
    "session",
    "mission",
    "business_proposal",
    "forbidden",
]

MemoryDecision = Literal[
    "allowed_within_mission",
    "blocked_cross_mission",
    "proposal_required",
    "promotion_allowed",
    "forbidden",
]


@dataclass(frozen=True)
class MissionMemoryRecord:
    mission_id: str
    mission_run_id: str
    key: str
    value_hash: str
    memory_scope: MissionMemoryScope
    data_retention_policy: str
    source_step_id: str
    record_hash: str = ""


@dataclass(frozen=True)
class MemoryPromotionProposal:
    source_mission_id: str
    target_business_id: str
    key: str
    proposed_value_hash: str
    reason: str
    proposed_by: str = "aion_pilot"
    approval_state: str = "pending_human_approval"
    proposal_hash: str = ""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def hash_memory_value(value: Any) -> str:
    return _hash({"memory_value": value})


def create_mission_memory_record(
    *,
    mission_id: str,
    mission_run_id: str,
    key: str,
    value: Any,
    memory_scope: MissionMemoryScope,
    data_retention_policy: str = "mission_scoped",
    source_step_id: str = "",
) -> dict[str, Any]:
    record = MissionMemoryRecord(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        key=key,
        value_hash=hash_memory_value(value),
        memory_scope=memory_scope,
        data_retention_policy=data_retention_policy,
        source_step_id=source_step_id,
    )
    data = asdict(record)
    data["record_hash"] = _hash({k: v for k, v in data.items() if k != "record_hash"})
    return data


def evaluate_memory_access(
    *,
    source_record: dict[str, Any],
    requesting_mission_id: str,
    approved_transfer_hash: str | None = None,
) -> dict[str, Any]:
    same_mission = source_record["mission_id"] == requesting_mission_id
    scope = source_record["memory_scope"]
    retention = source_record["data_retention_policy"]

    if scope == "forbidden":
        decision: MemoryDecision = "forbidden"
        allowed = False
        reason = "memory_scope_forbidden"
    elif same_mission and scope in {"session", "mission", "business_proposal"}:
        decision = "allowed_within_mission"
        allowed = True
        reason = "same_mission_access_allowed"
    elif retention == "mission_scoped" and not approved_transfer_hash:
        decision = "blocked_cross_mission"
        allowed = False
        reason = "mission_scoped_data_cannot_cross_mission_without_approval"
    elif scope == "business_proposal" and approved_transfer_hash:
        decision = "promotion_allowed"
        allowed = True
        reason = "approved_business_memory_transfer"
    else:
        decision = "proposal_required"
        allowed = False
        reason = "memory_promotion_proposal_required"

    result = {
        "schema_version": "aion.cross_mission_memory_access.v0",
        "source_mission_id": source_record["mission_id"],
        "requesting_mission_id": requesting_mission_id,
        "key": source_record["key"],
        "memory_scope": scope,
        "data_retention_policy": retention,
        "access_allowed": allowed,
        "decision": decision,
        "reason": reason,
        "approved_transfer_hash": approved_transfer_hash,
        "access_hash": "",
    }
    result["access_hash"] = _hash({k: v for k, v in result.items() if k != "access_hash"})
    return result


def create_memory_promotion_proposal(
    *,
    source_mission_id: str,
    target_business_id: str,
    key: str,
    value: Any,
    reason: str,
    proposed_by: str = "aion_pilot",
) -> dict[str, Any]:
    proposal = MemoryPromotionProposal(
        source_mission_id=source_mission_id,
        target_business_id=target_business_id,
        key=key,
        proposed_value_hash=hash_memory_value(value),
        reason=reason,
        proposed_by=proposed_by,
    )
    data = asdict(proposal)
    data["proposal_hash"] = _hash({k: v for k, v in data.items() if k != "proposal_hash"})
    return data


def approve_memory_promotion(
    *,
    proposal: dict[str, Any],
    approving_human: str,
) -> dict[str, Any]:
    approved = {
        **proposal,
        "approval_state": "approved",
        "approving_human": approving_human,
    }
    approved["approval_hash"] = _hash(approved)
    return approved


def block_accidental_memory_leakage(
    *,
    source_mission_id: str,
    target_mission_id: str,
    candidate_context: dict[str, Any],
    approved_transfer_hash: str | None = None,
) -> dict[str, Any]:
    contains_source_mission_data = source_mission_id in _canonical_json(candidate_context)

    blocked = (
        source_mission_id != target_mission_id
        and contains_source_mission_data
        and not approved_transfer_hash
    )

    result = {
        "schema_version": "aion.accidental_memory_leakage_guard.v0",
        "source_mission_id": source_mission_id,
        "target_mission_id": target_mission_id,
        "contains_source_mission_data": contains_source_mission_data,
        "approved_transfer_hash": approved_transfer_hash,
        "leakage_blocked": blocked,
        "context_allowed": not blocked,
        "reason": "accidental_cross_mission_leakage_blocked" if blocked else "context_allowed",
        "leakage_guard_hash": "",
    }
    result["leakage_guard_hash"] = _hash({k: v for k, v in result.items() if k != "leakage_guard_hash"})
    return result
