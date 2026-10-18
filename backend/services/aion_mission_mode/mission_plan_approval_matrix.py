"""
AION Phase 20N.1 — Mission Plan Approval Matrix

Plan-gated autonomy:
- Broad user goal becomes reviewable mission plan.
- Every step receives a control mode.
- User may make any step stricter.
- User may not downgrade system safety.
- Plan-level approval only approves mission shape.
- Exact payload approval is still required for risky live actions.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Any, Literal


ControlMode = Literal[
    "autonomous",
    "human_approval_required",
    "human_task_required",
    "blocked",
]

RiskLevel = Literal["low", "medium", "high", "critical"]

Lane = Literal[
    "research",
    "creation",
    "internal_ops",
    "external_action",
    "financial_action",
    "legal_action",
    "deployment_action",
    "memory_mutation",
]


SAFETY_ORDER: dict[str, int] = {
    "autonomous": 0,
    "human_approval_required": 1,
    "human_task_required": 2,
    "blocked": 3,
}


RISKY_LANES = {
    "external_action",
    "financial_action",
    "legal_action",
    "deployment_action",
    "memory_mutation",
}


HUMAN_TASK_ACTIONS = {
    "create_real_facebook_account",
    "verify_phone_number",
    "upload_identity_document",
    "answer_verification_call",
    "take_real_job_photos",
    "sign_legal_document",
    "provide_provider_access",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MissionPlanStep:
    step_id: str
    title: str
    description: str
    lane: Lane
    risk_level: RiskLevel
    action_type: str
    default_decision: ControlMode
    user_override: ControlMode | None
    effective_decision: ControlMode
    requires_human_approval: bool
    requires_human_task: bool
    can_run_autonomous: bool
    blocked: bool
    estimated_cost: float | None
    external_side_effect: bool
    provider: str | None
    payload_required_later: bool
    policy_override_violation: bool = False


def default_control_mode_for_step(step: dict[str, Any]) -> ControlMode:
    lane = step.get("lane", "internal_ops")
    action_type = step.get("action_type", "")
    risk = step.get("risk_level", "low")

    if action_type in HUMAN_TASK_ACTIONS:
        return "human_task_required"

    if risk == "critical":
        return "blocked"

    if lane in {"financial_action", "legal_action", "deployment_action", "memory_mutation"}:
        return "human_approval_required"

    if lane == "external_action":
        return "human_approval_required"

    if risk in {"high", "critical"}:
        return "human_approval_required"

    if risk == "medium":
        return "human_approval_required"

    return "autonomous"


def effective_control_mode(
    *,
    system_decision: ControlMode,
    user_override: ControlMode | None,
) -> tuple[ControlMode, bool]:
    if user_override is None:
        return system_decision, False

    system_rank = SAFETY_ORDER[system_decision]
    user_rank = SAFETY_ORDER[user_override]

    if user_rank < system_rank:
        return system_decision, True

    return user_override, False


def build_plan_step(raw_step: dict[str, Any]) -> dict[str, Any]:
    system_decision = raw_step.get("default_decision") or default_control_mode_for_step(raw_step)
    user_override = raw_step.get("user_override")
    effective, violation = effective_control_mode(
        system_decision=system_decision,
        user_override=user_override,
    )

    lane = raw_step.get("lane", "internal_ops")
    external_side_effect = bool(raw_step.get("external_side_effect", lane in RISKY_LANES))
    payload_required_later = bool(
        raw_step.get(
            "payload_required_later",
            effective == "human_approval_required" and external_side_effect,
        )
    )

    step = MissionPlanStep(
        step_id=raw_step["step_id"],
        title=raw_step["title"],
        description=raw_step.get("description", ""),
        lane=lane,
        risk_level=raw_step.get("risk_level", "low"),
        action_type=raw_step.get("action_type", raw_step["step_id"]),
        default_decision=system_decision,
        user_override=user_override,
        effective_decision=effective,
        requires_human_approval=effective == "human_approval_required",
        requires_human_task=effective == "human_task_required",
        can_run_autonomous=effective == "autonomous",
        blocked=effective == "blocked",
        estimated_cost=raw_step.get("estimated_cost"),
        external_side_effect=external_side_effect,
        provider=raw_step.get("provider"),
        payload_required_later=payload_required_later,
        policy_override_violation=violation,
    )
    return asdict(step)


def create_mission_plan_approval_matrix(
    *,
    mission_id: str,
    mission_run_id: str,
    plan_id: str,
    user_goal: str,
    raw_steps: list[dict[str, Any]],
    plan_version: int = 1,
    last_modified_by: str = "aion_pilot",
    change_reason: str = "initial_plan",
) -> dict[str, Any]:
    steps = [build_plan_step(step) for step in raw_steps]

    approval_count = sum(1 for step in steps if step["requires_human_approval"])
    human_task_count = sum(1 for step in steps if step["requires_human_task"])
    autonomous_count = sum(1 for step in steps if step["can_run_autonomous"])
    blocked_count = sum(1 for step in steps if step["blocked"])
    override_violation_count = sum(1 for step in steps if step["policy_override_violation"])

    matrix = {
        "schema_version": "aion.mission_plan_approval_matrix.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "plan_id": plan_id,
        "plan_version": plan_version,
        "user_goal": user_goal,
        "last_modified_by": last_modified_by,
        "change_reason": change_reason,
        "plan_level_approval_only": True,
        "payload_level_approval_still_required": True,
        "steps": steps,
        "step_count": len(steps),
        "autonomous_count": autonomous_count,
        "approval_count": approval_count,
        "human_task_count": human_task_count,
        "blocked_count": blocked_count,
        "policy_override_violation_count": override_violation_count,
        "runtime_mount_allowed": override_violation_count == 0,
        "plan_approval_matrix_hash": "",
    }
    matrix["plan_approval_matrix_hash"] = _hash(
        {k: v for k, v in matrix.items() if k != "plan_approval_matrix_hash"}
    )
    return matrix


def approve_plan_matrix(
    *,
    matrix: dict[str, Any],
    approving_human: str,
) -> dict[str, Any]:
    approval = {
        "schema_version": "aion.plan_level_approval.v0",
        "mission_id": matrix["mission_id"],
        "mission_run_id": matrix["mission_run_id"],
        "plan_id": matrix["plan_id"],
        "plan_version": matrix["plan_version"],
        "approving_human": approving_human,
        "approved_matrix_hash": matrix["plan_approval_matrix_hash"],
        "plan_level_approval_only": True,
        "payload_level_approval_still_required": True,
    }
    approval["plan_approval_hash"] = _hash(approval)
    return approval


def validate_plan_matrix_unchanged(
    *,
    approved_matrix_hash: str,
    current_matrix: dict[str, Any],
) -> dict[str, Any]:
    current_hash = current_matrix["plan_approval_matrix_hash"]
    unchanged = approved_matrix_hash == current_hash

    result = {
        "schema_version": "aion.plan_matrix_change_check.v0",
        "approved_matrix_hash": approved_matrix_hash,
        "current_matrix_hash": current_hash,
        "plan_unchanged": unchanged,
        "requires_re_review": not unchanged,
        "reason": "plan_matrix_unchanged" if unchanged else "plan_matrix_changed_after_approval",
        "validation_hash": "",
    }
    result["validation_hash"] = _hash({k: v for k, v in result.items() if k != "validation_hash"})
    return result


def example_roofing_business_plan() -> list[dict[str, Any]]:
    return [
        {
            "step_id": "define_offer",
            "title": "Define roofing business positioning and offer",
            "description": "Create the core Surrey roofing offer and service promise.",
            "lane": "creation",
            "risk_level": "low",
            "action_type": "generate_business_offer",
        },
        {
            "step_id": "brand_identity",
            "title": "Create brand identity direction",
            "description": "Draft name, message, colour direction, and visual style.",
            "lane": "creation",
            "risk_level": "low",
            "action_type": "create_brand_direction",
        },
        {
            "step_id": "check_domain",
            "title": "Check domain availability",
            "description": "Read-only domain lookup for shortlisted names.",
            "lane": "research",
            "risk_level": "low",
            "action_type": "domain_availability_check",
            "provider": "domain_provider",
            "external_side_effect": False,
        },
        {
            "step_id": "buy_domain",
            "title": "Buy selected domain name",
            "description": "Prepare checkout and request approval before purchase.",
            "lane": "financial_action",
            "risk_level": "high",
            "action_type": "buy_domain",
            "provider": "GoDaddy",
            "estimated_cost": 11.99,
            "external_side_effect": True,
            "payload_required_later": True,
        },
        {
            "step_id": "build_site",
            "title": "Build website locally",
            "description": "Create local website project, pages, copy, and assets.",
            "lane": "creation",
            "risk_level": "low",
            "action_type": "create_site_files",
        },
        {
            "step_id": "deploy_site",
            "title": "Deploy website to production",
            "description": "Deploy approved build to production hosting.",
            "lane": "deployment_action",
            "risk_level": "high",
            "action_type": "deploy_to_vercel_production",
            "provider": "Vercel",
            "external_side_effect": True,
            "payload_required_later": True,
        },
        {
            "step_id": "facebook_page",
            "title": "Create Facebook business page",
            "description": "Human creates or connects real Facebook page.",
            "lane": "external_action",
            "risk_level": "medium",
            "action_type": "create_real_facebook_account",
            "provider": "Meta",
            "external_side_effect": True,
        },
        {
            "step_id": "draft_posts",
            "title": "Draft first ten launch posts",
            "description": "Create launch content drafts.",
            "lane": "creation",
            "risk_level": "low",
            "action_type": "draft_social_posts",
        },
        {
            "step_id": "publish_first_post",
            "title": "Publish first Facebook post",
            "description": "Publish exact approved post payload.",
            "lane": "external_action",
            "risk_level": "high",
            "action_type": "publish_facebook_post",
            "provider": "Meta",
            "external_side_effect": True,
            "payload_required_later": True,
        },
        {
            "step_id": "launch_ad",
            "title": "Launch first paid advert",
            "description": "Launch approved paid campaign.",
            "lane": "financial_action",
            "risk_level": "high",
            "action_type": "start_ad_campaign",
            "provider": "Meta",
            "estimated_cost": 50.0,
            "external_side_effect": True,
            "payload_required_later": True,
        },
    ]
