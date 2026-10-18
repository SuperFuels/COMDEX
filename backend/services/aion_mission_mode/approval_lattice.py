"""
AION Phase 20N.4 — Approval Lattice + User Override Safety

Locks:
- Control modes form an ordered safety lattice.
- User may make a step stricter.
- User may not make system-controlled step looser.
- EffectiveDecision = supremum(SystemDecision, UserDecision).
- Unsafe downgrade fails closed and emits policy_override_violation.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Literal


ControlMode = Literal[
    "autonomous",
    "human_approval_required",
    "human_task_required",
    "blocked",
]


CONTROL_ORDER: dict[str, int] = {
    "autonomous": 0,
    "human_approval_required": 1,
    "human_task_required": 2,
    "blocked": 3,
}

ORDER_TO_CONTROL: dict[int, str] = {v: k for k, v in CONTROL_ORDER.items()}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def validate_control_mode(value: str) -> ControlMode:
    if value not in CONTROL_ORDER:
        raise ValueError(f"Unknown control mode: {value}")
    return value  # type: ignore[return-value]


def control_rank(mode: str) -> int:
    return CONTROL_ORDER[validate_control_mode(mode)]


def compare_control_modes(left: str, right: str) -> dict[str, Any]:
    left_rank = control_rank(left)
    right_rank = control_rank(right)

    if left_rank < right_rank:
        relation = "less_strict"
    elif left_rank > right_rank:
        relation = "more_strict"
    else:
        relation = "equal"

    result = {
        "schema_version": "aion.control_mode_comparison.v0",
        "left": left,
        "right": right,
        "left_rank": left_rank,
        "right_rank": right_rank,
        "relation": relation,
        "comparison_hash": "",
    }
    result["comparison_hash"] = _hash({k: v for k, v in result.items() if k != "comparison_hash"})
    return result


def supremum_control_mode(system_decision: str, user_decision: str | None) -> str:
    system_rank = control_rank(system_decision)

    if user_decision is None:
        return validate_control_mode(system_decision)

    user_rank = control_rank(user_decision)
    return ORDER_TO_CONTROL[max(system_rank, user_rank)]


def resolve_effective_decision(
    *,
    step_id: str,
    system_decision: str,
    user_override: str | None,
    actor: str = "user",
) -> dict[str, Any]:
    system_mode = validate_control_mode(system_decision)
    user_mode = validate_control_mode(user_override) if user_override is not None else None

    effective = supremum_control_mode(system_mode, user_mode)
    downgrade_attempted = user_mode is not None and control_rank(user_mode) < control_rank(system_mode)
    stricter_override = user_mode is not None and control_rank(user_mode) > control_rank(system_mode)

    result = {
        "schema_version": "aion.approval_lattice_resolution.v0",
        "step_id": step_id,
        "actor": actor,
        "system_decision": system_mode,
        "user_override": user_mode,
        "effective_decision": effective,
        "user_override_present": user_mode is not None,
        "stricter_override": stricter_override,
        "policy_override_violation": downgrade_attempted,
        "runtime_mount_allowed": not downgrade_attempted,
        "fail_closed": downgrade_attempted,
        "reason": (
            "policy_override_violation"
            if downgrade_attempted
            else "stricter_user_override_applied"
            if stricter_override
            else "system_decision_preserved"
            if user_mode is None
            else "equal_override"
        ),
        "lattice_resolution_hash": "",
    }
    result["lattice_resolution_hash"] = _hash(
        {k: v for k, v in result.items() if k != "lattice_resolution_hash"}
    )
    return result


def apply_lattice_to_plan_steps(
    *,
    mission_id: str,
    mission_run_id: str,
    plan_id: str,
    steps: list[dict[str, Any]],
    actor: str = "user",
) -> dict[str, Any]:
    resolutions: list[dict[str, Any]] = []

    for step in steps:
        resolutions.append(
            resolve_effective_decision(
                step_id=step["step_id"],
                system_decision=step.get("system_decision") or step.get("default_decision", "autonomous"),
                user_override=step.get("user_override"),
                actor=actor,
            )
        )

    violations = [r for r in resolutions if r["policy_override_violation"]]

    result = {
        "schema_version": "aion.plan_lattice_application.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "plan_id": plan_id,
        "resolutions": resolutions,
        "resolution_count": len(resolutions),
        "policy_override_violation_count": len(violations),
        "runtime_mount_allowed": len(violations) == 0,
        "fail_closed": len(violations) > 0,
        "plan_lattice_hash": "",
    }
    result["plan_lattice_hash"] = _hash({k: v for k, v in result.items() if k != "plan_lattice_hash"})
    return result


def strictness_sequence() -> list[str]:
    return [ORDER_TO_CONTROL[i] for i in sorted(ORDER_TO_CONTROL)]
