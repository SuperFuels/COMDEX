"""
AION Phase 20N.7 — Expiry Management + Stale Matrix Revocation

Locks:
- Plan approval matrix expiry.
- Sub-plan approval matrix expiry.
- Profile/budget freshness binding.
- Stale matrix revocation.
- Matrix expiry is separate from exact payload approval expiry in Phase 20R.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Literal


MatrixType = Literal[
    "mission_plan_matrix",
    "subplan_matrix",
    "profile_application",
    "budget_contract",
]


VALID_MATRIX_TYPES = {
    "mission_plan_matrix",
    "subplan_matrix",
    "profile_application",
    "budget_contract",
}


DEFAULT_TTL_SECONDS = {
    "mission_plan_matrix": 3600,
    "subplan_matrix": 1800,
    "profile_application": 3600,
    "budget_contract": 3600,
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def validate_matrix_type(matrix_type: str) -> MatrixType:
    if matrix_type not in VALID_MATRIX_TYPES:
        raise ValueError(f"Unknown matrix type: {matrix_type}")
    return matrix_type  # type: ignore[return-value]


def create_matrix_freshness_record(
    *,
    mission_id: str,
    mission_run_id: str,
    matrix_id: str,
    matrix_type: str,
    matrix_hash: str,
    issued_at: int,
    ttl_seconds: int | None = None,
    parent_matrix_hash: str | None = None,
    profile_application_hash: str | None = None,
    budget_hash: str | None = None,
) -> dict[str, Any]:
    matrix_type = validate_matrix_type(matrix_type)
    ttl = DEFAULT_TTL_SECONDS[matrix_type] if ttl_seconds is None else int(ttl_seconds)
    expires_at = int(issued_at) + ttl

    result = {
        "schema_version": "aion.matrix_freshness_record.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "matrix_id": matrix_id,
        "matrix_type": matrix_type,
        "matrix_hash": matrix_hash,
        "parent_matrix_hash": parent_matrix_hash,
        "profile_application_hash": profile_application_hash,
        "budget_hash": budget_hash,
        "issued_at": int(issued_at),
        "ttl_seconds": ttl,
        "expires_at": expires_at,
        "revoked": False,
        "revocation_reason": None,
        "freshness_record_hash": "",
    }
    result["freshness_record_hash"] = _hash(
        {k: v for k, v in result.items() if k != "freshness_record_hash"}
    )
    return result


def evaluate_matrix_freshness(
    *,
    record: dict[str, Any],
    evaluation_time: int,
    current_matrix_hash: str | None = None,
    current_parent_matrix_hash: str | None = None,
    current_profile_application_hash: str | None = None,
    current_budget_hash: str | None = None,
) -> dict[str, Any]:
    now = int(evaluation_time)
    expired = now > int(record["expires_at"])
    revoked = bool(record.get("revoked"))

    matrix_changed = (
        current_matrix_hash is not None
        and current_matrix_hash != record["matrix_hash"]
    )
    parent_changed = (
        current_parent_matrix_hash is not None
        and record.get("parent_matrix_hash") is not None
        and current_parent_matrix_hash != record.get("parent_matrix_hash")
    )
    profile_changed = (
        current_profile_application_hash is not None
        and record.get("profile_application_hash") is not None
        and current_profile_application_hash != record.get("profile_application_hash")
    )
    budget_changed = (
        current_budget_hash is not None
        and record.get("budget_hash") is not None
        and current_budget_hash != record.get("budget_hash")
    )

    stale = expired or revoked or matrix_changed or parent_changed or profile_changed or budget_changed

    reasons: list[str] = []
    if expired:
        reasons.append("matrix_expired")
    if revoked:
        reasons.append(record.get("revocation_reason") or "matrix_revoked")
    if matrix_changed:
        reasons.append("matrix_hash_changed")
    if parent_changed:
        reasons.append("parent_matrix_hash_changed")
    if profile_changed:
        reasons.append("profile_application_hash_changed")
    if budget_changed:
        reasons.append("budget_hash_changed")

    result = {
        "schema_version": "aion.matrix_freshness_evaluation.v0",
        "mission_id": record["mission_id"],
        "mission_run_id": record["mission_run_id"],
        "matrix_id": record["matrix_id"],
        "matrix_type": record["matrix_type"],
        "freshness_record_hash": record["freshness_record_hash"],
        "evaluation_time": now,
        "expired": expired,
        "revoked": revoked,
        "matrix_changed": matrix_changed,
        "parent_changed": parent_changed,
        "profile_changed": profile_changed,
        "budget_changed": budget_changed,
        "stale": stale,
        "runtime_mount_allowed": not stale,
        "mission_state": "waiting_human_review" if stale else "running_autonomous_steps",
        "requires_matrix_reapproval": stale,
        "reasons": reasons,
        "freshness_evaluation_hash": "",
    }
    result["freshness_evaluation_hash"] = _hash(
        {k: v for k, v in result.items() if k != "freshness_evaluation_hash"}
    )
    return result


def revoke_matrix_record(
    *,
    record: dict[str, Any],
    revoked_by: str,
    revocation_reason: str,
    revoked_at: int,
) -> dict[str, Any]:
    revoked = dict(record)
    revoked["revoked"] = True
    revoked["revoked_by"] = revoked_by
    revoked["revoked_at"] = int(revoked_at)
    revoked["revocation_reason"] = revocation_reason
    revoked.pop("freshness_record_hash", None)
    revoked["freshness_record_hash"] = _hash(
        {k: v for k, v in revoked.items() if k != "freshness_record_hash"}
    )
    return revoked


def create_stale_matrix_notice(
    *,
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    stale = bool(evaluation["stale"])
    result = {
        "schema_version": "aion.stale_matrix_notice.v0",
        "mission_id": evaluation["mission_id"],
        "mission_run_id": evaluation["mission_run_id"],
        "matrix_id": evaluation["matrix_id"],
        "matrix_type": evaluation["matrix_type"],
        "stale": stale,
        "requires_matrix_reapproval": evaluation["requires_matrix_reapproval"],
        "operator_message": (
            "Plan or matrix approval is stale. Review and approve the updated matrix before continuing."
            if stale
            else "Plan or matrix approval is fresh."
        ),
        "blocked_reason_codes": evaluation["reasons"],
        "notice_hash": "",
    }
    result["notice_hash"] = _hash({k: v for k, v in result.items() if k != "notice_hash"})
    return result


def assert_matrix_can_mount(
    *,
    record: dict[str, Any],
    evaluation_time: int,
    current_matrix_hash: str,
) -> dict[str, Any]:
    evaluation = evaluate_matrix_freshness(
        record=record,
        evaluation_time=evaluation_time,
        current_matrix_hash=current_matrix_hash,
    )

    result = {
        "schema_version": "aion.matrix_mount_assertion.v0",
        "mission_id": record["mission_id"],
        "mission_run_id": record["mission_run_id"],
        "matrix_id": record["matrix_id"],
        "matrix_type": record["matrix_type"],
        "runtime_mount_allowed": evaluation["runtime_mount_allowed"],
        "requires_matrix_reapproval": evaluation["requires_matrix_reapproval"],
        "mission_state": evaluation["mission_state"],
        "freshness_evaluation_hash": evaluation["freshness_evaluation_hash"],
        "mount_assertion_hash": "",
    }
    result["mount_assertion_hash"] = _hash(
        {k: v for k, v in result.items() if k != "mount_assertion_hash"}
    )
    return result
