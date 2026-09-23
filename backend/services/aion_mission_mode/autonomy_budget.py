"""
AION Phase 20N.6 — Autonomy Budget + Progressive Trust

Locks:
- Per-mission autonomy budget.
- External read, browser, runtime, safe step, sub-plan and total step caps.
- Spend/posts/deployments without approval remain zero by default.
- Trust ladder may allow more read/staged work, but never always-approval actions.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Literal


TrustLevel = Literal[
    "trust_0",
    "trust_1",
    "trust_2",
    "trust_3",
    "trust_4",
]


TRUST_LEVELS = {
    "trust_0": 0,
    "trust_1": 1,
    "trust_2": 2,
    "trust_3": 3,
    "trust_4": 4,
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
    "live_customer_message",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def validate_trust_level(trust_level: str) -> TrustLevel:
    if trust_level not in TRUST_LEVELS:
        raise ValueError(f"Unknown trust level: {trust_level}")
    return trust_level  # type: ignore[return-value]


def default_autonomy_budget(
    *,
    mission_id: str,
    mission_run_id: str,
    trust_level: str = "trust_0",
) -> dict[str, Any]:
    validate_trust_level(trust_level)
    rank = TRUST_LEVELS[trust_level]

    budget_by_level = {
        0: dict(max_external_reads=0, max_browser_sessions=0, max_runtime_minutes=10, max_safe_steps_before_review=10),
        1: dict(max_external_reads=10, max_browser_sessions=1, max_runtime_minutes=20, max_safe_steps_before_review=20),
        2: dict(max_external_reads=25, max_browser_sessions=3, max_runtime_minutes=45, max_safe_steps_before_review=35),
        3: dict(max_external_reads=50, max_browser_sessions=5, max_runtime_minutes=90, max_safe_steps_before_review=50),
        4: dict(max_external_reads=100, max_browser_sessions=10, max_runtime_minutes=120, max_safe_steps_before_review=75),
    }[rank]

    result = {
        "schema_version": "aion.autonomy_budget.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "trust_level": trust_level,
        **budget_by_level,
        "max_subplan_depth": 3,
        "max_total_steps": 100,
        "max_spend_without_payload_approval": 0,
        "max_public_posts_without_approval": 0,
        "max_production_deployments_without_approval": 0,
        "max_live_customer_messages_without_approval": 0,
        "budget_hash": "",
    }
    result["budget_hash"] = _hash({k: v for k, v in result.items() if k != "budget_hash"})
    return result


def create_usage_snapshot(
    *,
    mission_id: str,
    mission_run_id: str,
    external_reads_used: int = 0,
    browser_sessions_used: int = 0,
    runtime_minutes_used: float = 0,
    safe_steps_since_review: int = 0,
    subplan_depth: int = 0,
    total_steps: int = 0,
    spend_without_payload_approval: float = 0,
    public_posts_without_approval: int = 0,
    production_deployments_without_approval: int = 0,
    live_customer_messages_without_approval: int = 0,
) -> dict[str, Any]:
    result = {
        "schema_version": "aion.autonomy_budget_usage.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "external_reads_used": external_reads_used,
        "browser_sessions_used": browser_sessions_used,
        "runtime_minutes_used": round(float(runtime_minutes_used), 2),
        "safe_steps_since_review": safe_steps_since_review,
        "subplan_depth": subplan_depth,
        "total_steps": total_steps,
        "spend_without_payload_approval": round(float(spend_without_payload_approval), 2),
        "public_posts_without_approval": public_posts_without_approval,
        "production_deployments_without_approval": production_deployments_without_approval,
        "live_customer_messages_without_approval": live_customer_messages_without_approval,
        "usage_hash": "",
    }
    result["usage_hash"] = _hash({k: v for k, v in result.items() if k != "usage_hash"})
    return result


def evaluate_budget(
    *,
    budget: dict[str, Any],
    usage: dict[str, Any],
) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []

    checks = [
        ("external_reads", usage["external_reads_used"], budget["max_external_reads"]),
        ("browser_sessions", usage["browser_sessions_used"], budget["max_browser_sessions"]),
        ("runtime_minutes", usage["runtime_minutes_used"], budget["max_runtime_minutes"]),
        ("safe_steps_before_review", usage["safe_steps_since_review"], budget["max_safe_steps_before_review"]),
        ("subplan_depth", usage["subplan_depth"], budget["max_subplan_depth"]),
        ("total_steps", usage["total_steps"], budget["max_total_steps"]),
        ("spend_without_payload_approval", usage["spend_without_payload_approval"], budget["max_spend_without_payload_approval"]),
        ("public_posts_without_approval", usage["public_posts_without_approval"], budget["max_public_posts_without_approval"]),
        ("production_deployments_without_approval", usage["production_deployments_without_approval"], budget["max_production_deployments_without_approval"]),
        ("live_customer_messages_without_approval", usage["live_customer_messages_without_approval"], budget["max_live_customer_messages_without_approval"]),
    ]

    for name, used, limit in checks:
        if used > limit:
            violations.append(
                {
                    "metric": name,
                    "used": used,
                    "limit": limit,
                    "violation_type": "budget_exceeded",
                }
            )

    allowed = len(violations) == 0
    result = {
        "schema_version": "aion.autonomy_budget_evaluation.v0",
        "mission_id": budget["mission_id"],
        "mission_run_id": budget["mission_run_id"],
        "trust_level": budget["trust_level"],
        "budget_hash": budget["budget_hash"],
        "usage_hash": usage["usage_hash"],
        "allowed": allowed,
        "mission_state": "running_autonomous_steps" if allowed else "waiting_human_review",
        "violation_count": len(violations),
        "violations": violations,
        "evaluation_hash": "",
    }
    result["evaluation_hash"] = _hash({k: v for k, v in result.items() if k != "evaluation_hash"})
    return result


def trust_ladder_policy(trust_level: str) -> dict[str, Any]:
    validate_trust_level(trust_level)
    rank = TRUST_LEVELS[trust_level]

    result = {
        "schema_version": "aion.trust_ladder_policy.v0",
        "trust_level": trust_level,
        "rank": rank,
        "read_only_external_allowed": rank >= 1,
        "preview_deploys_allowed": rank >= 2,
        "recurring_template_content_allowed": rank >= 3,
        "small_recurring_budget_possible_under_governance": rank >= 4,
        "always_approval_actions_remain_approval_required": True,
        "policy_hash": "",
    }
    result["policy_hash"] = _hash({k: v for k, v in result.items() if k != "policy_hash"})
    return result


def action_requires_approval_under_budget(
    *,
    action_type: str,
    trust_level: str,
) -> dict[str, Any]:
    validate_trust_level(trust_level)
    always_required = action_type in ALWAYS_APPROVAL_ACTION_TYPES

    result = {
        "schema_version": "aion.action_budget_approval_requirement.v0",
        "action_type": action_type,
        "trust_level": trust_level,
        "always_approval_action": always_required,
        "approval_required": always_required,
        "reason": "always_approval_action" if always_required else "not_forced_by_budget_layer",
        "requirement_hash": "",
    }
    result["requirement_hash"] = _hash({k: v for k, v in result.items() if k != "requirement_hash"})
    return result


def update_usage_after_event(
    *,
    usage: dict[str, Any],
    event_type: str,
    amount: float | int = 1,
) -> dict[str, Any]:
    updated = dict(usage)
    updated.pop("usage_hash", None)

    if event_type == "external_read":
        updated["external_reads_used"] += int(amount)
    elif event_type == "browser_session":
        updated["browser_sessions_used"] += int(amount)
    elif event_type == "runtime_minutes":
        updated["runtime_minutes_used"] = round(float(updated["runtime_minutes_used"]) + float(amount), 2)
    elif event_type == "safe_step":
        updated["safe_steps_since_review"] += int(amount)
    elif event_type == "subplan_depth":
        updated["subplan_depth"] += int(amount)
    elif event_type == "total_step":
        updated["total_steps"] += int(amount)
    elif event_type == "unapproved_spend":
        updated["spend_without_payload_approval"] = round(float(updated["spend_without_payload_approval"]) + float(amount), 2)
    elif event_type == "unapproved_public_post":
        updated["public_posts_without_approval"] += int(amount)
    elif event_type == "unapproved_production_deploy":
        updated["production_deployments_without_approval"] += int(amount)
    elif event_type == "unapproved_live_customer_message":
        updated["live_customer_messages_without_approval"] += int(amount)
    else:
        raise ValueError(f"Unknown usage event type: {event_type}")

    updated["usage_hash"] = _hash({k: v for k, v in updated.items() if k != "usage_hash"})
    return updated
