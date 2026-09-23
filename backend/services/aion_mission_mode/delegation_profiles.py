"""
AION Phase 20N.5 — Delegation Profiles / Autonomy Modes

Locks:
- Delegation profiles pre-populate mission autonomy defaults.
- Profiles never bypass system safety.
- Profiles feed through the approval lattice.
- Emergency Lockdown makes everything non-autonomous.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Literal

from backend.services.aion_mission_mode.approval_lattice import (
    apply_lattice_to_plan_steps,
    CONTROL_ORDER,
)


DelegationProfile = Literal[
    "safe_draft_mode",
    "business_setup_mode",
    "trusted_operator_mode",
    "emergency_lockdown_mode",
]


PROFILE_ORDER = [
    "safe_draft_mode",
    "business_setup_mode",
    "trusted_operator_mode",
    "emergency_lockdown_mode",
]


RISKY_LANES = {
    "external_action",
    "financial_action",
    "legal_action",
    "deployment_action",
    "memory_mutation",
    "customer_message",
    "public_publish",
    "identity_action",
}


ALWAYS_APPROVAL_ACTION_TYPES = {
    "buy_domain",
    "pay_for_hosting",
    "deploy_to_production",
    "connect_dns",
    "publish_facebook_post",
    "send_email_campaign",
    "send_whatsapp_message",
    "start_ad_campaign",
    "take_payment",
    "create_booking",
    "submit_legal_document",
    "submit_identity_document",
}


HUMAN_TASK_ACTION_TYPES = {
    "create_real_facebook_account",
    "create_google_business_profile",
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


def validate_profile(profile: str) -> DelegationProfile:
    if profile not in PROFILE_ORDER:
        raise ValueError(f"Unknown delegation profile: {profile}")
    return profile  # type: ignore[return-value]


def profile_defaults(profile: str) -> dict[str, Any]:
    validate_profile(profile)

    defaults = {
        "safe_draft_mode": {
            "description": "Drafts/previews only. No external side effects.",
            "default_safe_internal": "autonomous",
            "default_read_only_external": "human_approval_required",
            "default_staged_external": "human_approval_required",
            "default_live_external": "human_approval_required",
            "max_external_reads": 0,
            "max_browser_sessions": 0,
            "max_spend_without_payload_approval": 0,
            "max_public_posts_without_approval": 0,
            "max_deployments_without_approval": 0,
        },
        "business_setup_mode": {
            "description": "Build and prepare work autonomously; pause for spend, deploy, publish, send or ownership actions.",
            "default_safe_internal": "autonomous",
            "default_read_only_external": "autonomous",
            "default_staged_external": "human_approval_required",
            "default_live_external": "human_approval_required",
            "max_external_reads": 25,
            "max_browser_sessions": 3,
            "max_spend_without_payload_approval": 0,
            "max_public_posts_without_approval": 0,
            "max_deployments_without_approval": 0,
        },
        "trusted_operator_mode": {
            "description": "Allows more read-only and staged operations under caps; live high-risk actions still require approval.",
            "default_safe_internal": "autonomous",
            "default_read_only_external": "autonomous",
            "default_staged_external": "autonomous",
            "default_live_external": "human_approval_required",
            "max_external_reads": 100,
            "max_browser_sessions": 10,
            "max_spend_without_payload_approval": 0,
            "max_public_posts_without_approval": 0,
            "max_deployments_without_approval": 0,
        },
        "emergency_lockdown_mode": {
            "description": "Read-only proof/replay mode. No autonomous execution.",
            "default_safe_internal": "blocked",
            "default_read_only_external": "blocked",
            "default_staged_external": "blocked",
            "default_live_external": "blocked",
            "max_external_reads": 0,
            "max_browser_sessions": 0,
            "max_spend_without_payload_approval": 0,
            "max_public_posts_without_approval": 0,
            "max_deployments_without_approval": 0,
        },
    }[profile]

    result = {
        "schema_version": "aion.delegation_profile_defaults.v0",
        "profile": profile,
        **defaults,
        "profile_defaults_hash": "",
    }
    result["profile_defaults_hash"] = _hash({k: v for k, v in result.items() if k != "profile_defaults_hash"})
    return result


def classify_step_tool_mode(step: dict[str, Any]) -> str:
    if step.get("tool_mode"):
        return step["tool_mode"]

    lane = step.get("lane", "creation")
    action_type = step.get("action_type", "")

    # Explicit action type beats the default lane. A step such as
    # prepare_vercel_deploy may omit lane and would otherwise default to
    # creation, incorrectly classifying it as safe_internal.
    if action_type.startswith("prepare_") or lane == "staged_external":
        return "staged_external"

    if action_type in ALWAYS_APPROVAL_ACTION_TYPES:
        return "approved_live_external"

    if lane in {"read_only_external", "research"}:
        return "read_only_external"

    if lane in RISKY_LANES:
        return "approved_live_external"

    if lane in {"creation", "internal_ops", "analysis", "drafting"}:
        return "safe_internal"

    return "safe_internal"


def profile_default_decision_for_step(profile: str, step: dict[str, Any]) -> str:
    defaults = profile_defaults(profile)

    action_type = step.get("action_type", "")
    lane = step.get("lane", "creation")
    tool_mode = classify_step_tool_mode(step)

    if profile == "emergency_lockdown_mode":
        return "blocked"

    if action_type in HUMAN_TASK_ACTION_TYPES:
        return "human_task_required"

    if action_type in ALWAYS_APPROVAL_ACTION_TYPES:
        return "human_approval_required"

    if lane in {"legal_action", "identity_action"}:
        return "human_task_required"

    if tool_mode == "safe_internal":
        return defaults["default_safe_internal"]

    if tool_mode == "read_only_external":
        return defaults["default_read_only_external"]

    if tool_mode == "staged_external":
        return defaults["default_staged_external"]

    if tool_mode == "approved_live_external":
        return defaults["default_live_external"]

    return "human_approval_required"


def apply_delegation_profile_to_steps(
    *,
    mission_id: str,
    mission_run_id: str,
    plan_id: str,
    profile: str,
    steps: list[dict[str, Any]],
    actor: str = "system",
) -> dict[str, Any]:
    validate_profile(profile)
    defaults = profile_defaults(profile)

    profiled_steps: list[dict[str, Any]] = []
    for step in steps:
        system_decision = step.get("system_decision") or step.get("default_decision") or "autonomous"
        profile_decision = profile_default_decision_for_step(profile, step)

        # Profile acts as user/default preference, then lattice clamps to system decision.
        profiled_step = {
            **step,
            "system_decision": system_decision,
            "profile": profile,
            "profile_default_decision": profile_decision,
            "user_override": step.get("user_override", profile_decision),
            "tool_mode": classify_step_tool_mode(step),
        }
        profiled_steps.append(profiled_step)

    lattice = apply_lattice_to_plan_steps(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        plan_id=plan_id,
        steps=profiled_steps,
        actor=actor,
    )

    result = {
        "schema_version": "aion.delegation_profile_application.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "plan_id": plan_id,
        "profile": profile,
        "profile_defaults": defaults,
        "profiled_steps": profiled_steps,
        "lattice_result": lattice,
        "runtime_mount_allowed": lattice["runtime_mount_allowed"],
        "profile_application_hash": "",
    }
    result["profile_application_hash"] = _hash(
        {k: v for k, v in result.items() if k != "profile_application_hash"}
    )
    return result


def profile_summary(profile: str) -> dict[str, Any]:
    defaults = profile_defaults(profile)
    result = {
        "schema_version": "aion.delegation_profile_summary.v0",
        "profile": profile,
        "description": defaults["description"],
        "external_reads_allowed": defaults["max_external_reads"] > 0,
        "browser_sessions_allowed": defaults["max_browser_sessions"] > 0,
        "unapproved_spend_allowed": defaults["max_spend_without_payload_approval"] > 0,
        "unapproved_public_posts_allowed": defaults["max_public_posts_without_approval"] > 0,
        "unapproved_deployments_allowed": defaults["max_deployments_without_approval"] > 0,
        "summary_hash": "",
    }
    result["summary_hash"] = _hash({k: v for k, v in result.items() if k != "summary_hash"})
    return result
