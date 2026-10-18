"""
AION Phase 20C Mission Planner v0

Deterministic planner mock for AION Pilot / Mission Mode.

Contract:
- No LLM calls.
- No live tools.
- No external writes.
- No bookings, payments, escrow, deploys, emails, WhatsApp sends, or reputation mutation.
- Converts mission goal + template into stable mission plan structure.
- Produces deterministic plan_hash.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Any

from backend.services.aion_mission_mode.mission_contract import (
    AionMissionContract,
    MissionCheckpoint,
    MissionMode,
)
from backend.services.aion_mission_mode.mission_templates import (
    get_mission_template,
)


SAFE_RESEARCH_ACTIONS = {
    "research_service_angle",
    "analyse_local_market",
    "summarise_context",
    "compare_options",
}

SAFE_CREATION_ACTIONS = {
    "draft_offer",
    "draft_facebook_advert",
    "draft_landing_page_copy",
    "draft_lead_form_questions",
    "create_workflow_preview",
    "create_agentmap_preview",
    "create_quote_intake_preview",
    "create_boardroom_summary",
    "create_campaign_pack",
}

CHECKPOINT_ACTIONS = {
    "publish_advert",
    "send_customer_message",
    "spend_money",
    "create_booking",
    "deploy_live_page",
    "take_payment",
    "create_escrow",
    "dispatch_worker",
}

BLOCKED_ACTIONS = {
    "send_whatsapp_live",
    "send_email_live",
    "capture_payment_live",
    "create_booking_live",
    "deploy_production_live",
    "write_live_reputation",
}


@dataclass(frozen=True)
class MissionPlanStep:
    step_id: str
    title: str
    action_type: str
    lane: str
    decision: str
    requires_checkpoint: bool
    produces_artifact: bool = False
    artifact_type: str | None = None
    preferred_sub_container: str | None = None


@dataclass(frozen=True)
class MissionPlan:
    mission_id: str
    mission_goal: str
    business_id: str
    template_id: str
    steps: list[dict[str, Any]]
    checkpoints: list[dict[str, Any]]
    blocked_actions: list[str]
    final_output_targets: list[str]
    plan_hash: str
    dry_run_only: bool
    live_side_effects_enabled: bool
    created_by: str = "aion_pilot"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _slug(value: str) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def _classify_action(action_type: str) -> tuple[str, str, bool]:
    action = _slug(action_type)

    if action in SAFE_RESEARCH_ACTIONS:
        return "research", "safe_autonomous", False

    if action in SAFE_CREATION_ACTIONS:
        return "creation", "safe_autonomous", False

    if action in CHECKPOINT_ACTIONS:
        if action in {"spend_money", "take_payment", "create_escrow"}:
            return "financial_action", "checkpoint_required", True
        if action in {"deploy_live_page"}:
            return "deployment_action", "checkpoint_required", True
        return "external_action", "checkpoint_required", True

    if action in BLOCKED_ACTIONS:
        return "external_action", "blocked", True

    return "internal_ops", "safe_autonomous", False


def _default_home_fixed_steps() -> list[dict[str, Any]]:
    return [
        {
            "title": "Research Home Fixed roof repair and outdoor living service angle",
            "action_type": "research_service_angle",
            "produces_artifact": False,
        },
        {
            "title": "Draft campaign offer",
            "action_type": "draft_offer",
            "produces_artifact": True,
            "artifact_type": "campaign_offer",
            "preferred_sub_container": "campaigns",
        },
        {
            "title": "Draft Facebook advert",
            "action_type": "draft_facebook_advert",
            "produces_artifact": True,
            "artifact_type": "advert_draft",
            "preferred_sub_container": "campaigns",
        },
        {
            "title": "Draft landing page copy",
            "action_type": "draft_landing_page_copy",
            "produces_artifact": True,
            "artifact_type": "landing_page_copy",
            "preferred_sub_container": "campaigns",
        },
        {
            "title": "Create workflow capsule preview",
            "action_type": "create_workflow_preview",
            "produces_artifact": True,
            "artifact_type": "workflow_preview",
            "preferred_sub_container": "workflows",
        },
        {
            "title": "Create AgentMap update preview",
            "action_type": "create_agentmap_preview",
            "produces_artifact": True,
            "artifact_type": "agentmap_preview",
            "preferred_sub_container": "agentmaps",
        },
        {
            "title": "Prepare publish approval checkpoint",
            "action_type": "publish_advert",
            "produces_artifact": True,
            "artifact_type": "approval_payload",
            "preferred_sub_container": "approvals",
        },
    ]


def _steps_from_template(template_id: str) -> list[dict[str, Any]]:
    template = get_mission_template(template_id)

    action_aliases = {
        "research_service_angle": "research_service_angle",
        "draft_offer": "draft_offer",
        "draft_advert": "draft_facebook_advert",
        "draft_facebook_advert": "draft_facebook_advert",
        "draft_landing_copy": "draft_landing_page_copy",
        "draft_landing_page_copy": "draft_landing_page_copy",
        "create_workflow_preview": "create_workflow_preview",
        "create_agentmap_preview": "create_agentmap_preview",
        "approve_publish": "publish_advert",
        "approve_public_launch": "publish_advert",
    }

    artifact_targets = {
        "draft_offer": ("campaign_offer", "campaigns"),
        "draft_facebook_advert": ("advert_draft", "campaigns"),
        "draft_landing_page_copy": ("landing_page_copy", "campaigns"),
        "create_workflow_preview": ("workflow_preview", "workflows"),
        "create_agentmap_preview": ("agentmap_preview", "agentmaps"),
        "create_quote_intake_preview": ("quote_intake_preview", "quotes"),
        "publish_advert": ("approval_payload", "approvals"),
    }

    translated: list[dict[str, Any]] = []

    for raw in template.get("steps", []):
        raw_action = str(raw.get("action_type") or raw.get("step_id") or raw.get("id") or "summarise_context")
        action_type = action_aliases.get(raw_action, raw_action)
        artifact = artifact_targets.get(action_type)

        step = {
            "title": str(raw.get("title") or action_type.replace("_", " ").title()),
            "action_type": action_type,
            "description": str(raw.get("description") or ""),
        }

        if artifact:
            step["produces_artifact"] = True
            step["artifact_type"] = artifact[0]
            step["preferred_sub_container"] = artifact[1]
        else:
            step["produces_artifact"] = False

        translated.append(step)

    return translated



def build_deterministic_mission_plan(
    *,
    contract: AionMissionContract,
    template_id: str = "home_fixed_lead_campaign_v0",
) -> dict[str, Any]:
    """
    Compile a deterministic mission plan from a Mission Contract and optional template.

    This is intentionally a mock planner. It exists before 20K LLM adapters so the
    runtime, hashes, checkpoints, proof and Boardroom can be built against stable data.
    """

    raw_steps = _steps_from_template(template_id)

    steps: list[MissionPlanStep] = []
    checkpoints: list[dict[str, Any]] = []
    blocked_actions: list[str] = []
    final_output_targets: list[str] = []

    for index, raw in enumerate(raw_steps, start=1):
        action_type = _slug(raw.get("action_type", "summarise_context"))
        lane, decision, requires_checkpoint = _classify_action(action_type)

        step_id = f"step_{index:02d}_{action_type}"

        step = MissionPlanStep(
            step_id=step_id,
            title=str(raw.get("title") or action_type.replace("_", " ").title()),
            action_type=action_type,
            lane=lane,
            decision=decision,
            requires_checkpoint=requires_checkpoint,
            produces_artifact=bool(raw.get("produces_artifact", False)),
            artifact_type=raw.get("artifact_type"),
            preferred_sub_container=raw.get("preferred_sub_container"),
        )

        steps.append(step)

        if step.produces_artifact and step.artifact_type:
            final_output_targets.append(str(step.artifact_type))

        if decision == "blocked":
            blocked_actions.append(action_type)

        if requires_checkpoint:
            checkpoint_payload = {
                "checkpoint_id": f"checkpoint_{index:02d}_{action_type}",
                "step_id": step_id,
                "title": step.title,
                "action_type": action_type,
                "lane": lane,
                "reason": "Action requires human approval before live execution.",
                "payload_hash": _hash(
                    {
                        "mission_id": contract.mission_id,
                        "step_id": step_id,
                        "action_type": action_type,
                        "title": step.title,
                    }
                ),
            }
            checkpoints.append(checkpoint_payload)

    plan_identity = {
        "mission_id": contract.mission_id,
        "mission_goal": contract.mission_goal,
        "business_id": contract.business_id,
        "template_id": template_id,
        "steps": [asdict(step) for step in steps],
        "checkpoints": checkpoints,
        "blocked_actions": blocked_actions,
        "final_output_targets": sorted(set(final_output_targets)),
        "dry_run_only": True,
        "live_side_effects_enabled": False,
    }

    plan = MissionPlan(
        mission_id=contract.mission_id,
        mission_goal=contract.mission_goal,
        business_id=contract.business_id,
        template_id=template_id,
        steps=[asdict(step) for step in steps],
        checkpoints=checkpoints,
        blocked_actions=blocked_actions,
        final_output_targets=sorted(set(final_output_targets)),
        plan_hash=_hash(plan_identity),
        dry_run_only=True,
        live_side_effects_enabled=False,
    )

    return asdict(plan)


def create_home_fixed_lead_campaign_plan() -> dict[str, Any]:
    contract = AionMissionContract(
        mission_id="mission_home_fixed_lead_campaign_001",
        mission_goal="Build a Home Fixed lead generation campaign for roof repairs and outdoor living work.",
        business_id="home_fixed",
        creator_id="kevin",
        agent_mode=MissionMode.CHECKPOINTED_AUTONOMY,
        allowed_autonomy_lanes=[
            "research",
            "creation",
            "internal_ops",
        ],
        hard_blocked_lanes=[
            "financial_action",
            "legal_action",
            "deployment_action",
        ],
        human_checkpoints=[
            MissionCheckpoint(
                checkpoint_id="checkpoint_publish_approval",
                title="Approve campaign before publishing",
                description="Approve exact campaign payload before publishing or sending externally.",
                required_before_step_id="step_07_publish_advert",
                lane="external_action",
                action_type="publish_advert",
                required_action_type="publish_advert",
            )
        ],
        approval_required_actions=[
            "publish_advert",
            "send_customer_message",
            "spend_money",
            "create_booking",
            "deploy_live_page",
            "take_payment",
            "create_escrow",
            "dispatch_worker",
        ],
        max_runtime_seconds=1800,
        max_tool_calls=40,
        max_cost=0.0,
        proof_required=True,
        replay_required=True,
        ets_enabled=True,
        data_retention_policy="mission_scoped",
        external_communication_consent_required=True,
        proof_sharing_enabled=False,
    )

    return build_deterministic_mission_plan(
        contract=contract,
        template_id="home_fixed_lead_campaign_v0",
    )
