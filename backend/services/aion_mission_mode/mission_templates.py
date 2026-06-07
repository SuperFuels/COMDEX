"""
AION Phase 20B — Mission Template v0

Mission templates convert common business objectives into deterministic
Mission Contract draft inputs.

This is template/planning infrastructure only:
- no live tools
- no external writes
- no payments
- no bookings
- no deployment
- no messaging
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any


TEMPLATE_VERSION = "aion.mission_template.v0"


SAFE_DEFAULT_LANES = [
    "research",
    "creation",
    "internal_ops",
]

DEFAULT_HARD_BLOCKED_LANES = [
    "external_action",
    "financial_action",
    "legal_action",
    "deployment_action",
    "memory_mutation",
]


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def stable_hash(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


MISSION_TEMPLATE_REGISTRY: dict[str, dict[str, Any]] = {
    "home_fixed_lead_campaign_v0": {
        "template_id": "home_fixed_lead_campaign_v0",
        "template_version": TEMPLATE_VERSION,
        "name": "Home Fixed Lead Campaign",
        "business_vertical": "home_repair",
        "mission_goal": "Build a Home Fixed lead generation campaign for roof repairs and outdoor living work.",
        "allowed_autonomy_lanes": SAFE_DEFAULT_LANES,
        "hard_blocked_lanes": DEFAULT_HARD_BLOCKED_LANES,
        "steps": [
            {
                "step_id": "research_service_angle",
                "title": "Research service angle",
                "lane": "research",
                "classification": "safe_autonomous",
                "description": "Review target services and produce campaign angles.",
            },
            {
                "step_id": "draft_offer",
                "title": "Draft offer",
                "lane": "creation",
                "classification": "safe_autonomous",
                "description": "Create a draft offer for roof repairs and outdoor living work.",
            },
            {
                "step_id": "draft_facebook_advert",
                "title": "Draft Facebook advert",
                "lane": "creation",
                "classification": "safe_autonomous",
                "description": "Create draft advert copy and creative notes.",
            },
            {
                "step_id": "draft_landing_page_copy",
                "title": "Draft landing page copy",
                "lane": "creation",
                "classification": "safe_autonomous",
                "description": "Create draft landing page sections and lead form questions.",
            },
            {
                "step_id": "create_workflow_preview",
                "title": "Create workflow capsule preview",
                "lane": "internal_ops",
                "classification": "safe_autonomous",
                "description": "Create preview-only intake workflow structure.",
            },
            {
                "step_id": "create_agentmap_preview",
                "title": "Create AgentMap preview",
                "lane": "internal_ops",
                "classification": "safe_autonomous",
                "description": "Create preview-only AgentMap capability update for the campaign.",
            },
            {
                "step_id": "approve_publish",
                "title": "Approve public launch",
                "lane": "external_action",
                "classification": "checkpoint_required",
                "description": "Pause before publishing, sending, spending, booking, deploying, payment, escrow or dispatch.",
            },
        ],
        "human_checkpoints": [
            {
                "checkpoint_id": "approve_campaign_package",
                "title": "Approve campaign package",
                "required_before": ["approve_publish"],
                "approval_required_actions": [
                    "publish_advert",
                    "send_message",
                    "spend_money",
                    "create_booking",
                    "deploy_page",
                    "take_payment",
                    "create_escrow",
                    "dispatch_worker",
                ],
            }
        ],
        "outputs": [
            "campaign_pack",
            "mission_receipt_preview",
            "proof_trace_preview",
            "ets_preview",
            "boardroom_summary",
        ],
    },
    "home_fixed_quote_intake_v0": {
        "template_id": "home_fixed_quote_intake_v0",
        "template_version": TEMPLATE_VERSION,
        "name": "Home Fixed Quote Intake",
        "business_vertical": "home_repair",
        "mission_goal": "Prepare a safe quote intake flow for Home Fixed customer requests.",
        "allowed_autonomy_lanes": SAFE_DEFAULT_LANES,
        "hard_blocked_lanes": DEFAULT_HARD_BLOCKED_LANES,
        "steps": [
            {
                "step_id": "draft_intake_questions",
                "title": "Draft intake questions",
                "lane": "creation",
                "classification": "safe_autonomous",
                "description": "Create quote intake questions for photos, location, job type and urgency.",
            },
            {
                "step_id": "create_quote_preview",
                "title": "Create quote preview structure",
                "lane": "internal_ops",
                "classification": "safe_autonomous",
                "description": "Create preview-only quote output structure.",
            },
            {
                "step_id": "approve_customer_message",
                "title": "Approve customer message",
                "lane": "external_action",
                "classification": "checkpoint_required",
                "description": "Pause before sending any customer message.",
            },
        ],
        "human_checkpoints": [
            {
                "checkpoint_id": "approve_customer_reply",
                "title": "Approve exact customer reply",
                "required_before": ["approve_customer_message"],
                "approval_required_actions": ["send_message", "confirm_booking", "take_payment"],
            }
        ],
        "outputs": ["quote_intake_preview", "message_draft", "mission_receipt_preview"],
    },
    "weekly_marketing_pack_v0": {
        "template_id": "weekly_marketing_pack_v0",
        "template_version": TEMPLATE_VERSION,
        "name": "Weekly Marketing Pack",
        "business_vertical": "general_sme",
        "mission_goal": "Create a weekly marketing pack with draft posts, offers and follow-up ideas.",
        "allowed_autonomy_lanes": SAFE_DEFAULT_LANES,
        "hard_blocked_lanes": DEFAULT_HARD_BLOCKED_LANES,
        "steps": [
            {
                "step_id": "review_business_focus",
                "title": "Review business focus",
                "lane": "research",
                "classification": "safe_autonomous",
                "description": "Summarise current services and suitable weekly marketing themes.",
            },
            {
                "step_id": "draft_posts",
                "title": "Draft social posts",
                "lane": "creation",
                "classification": "safe_autonomous",
                "description": "Create draft posts only.",
            },
            {
                "step_id": "approve_publish",
                "title": "Approve publishing",
                "lane": "external_action",
                "classification": "checkpoint_required",
                "description": "Pause before publishing or spending.",
            },
        ],
        "human_checkpoints": [
            {
                "checkpoint_id": "approve_posting",
                "title": "Approve exact post payload",
                "required_before": ["approve_publish"],
                "approval_required_actions": ["publish_post", "spend_money", "send_message"],
            }
        ],
        "outputs": ["weekly_marketing_pack", "post_drafts", "mission_receipt_preview"],
    },
    "generic_business_build_pack_v0": {
        "template_id": "generic_business_build_pack_v0",
        "template_version": TEMPLATE_VERSION,
        "name": "Generic Business Build Pack",
        "business_vertical": "general_business",
        "mission_goal": "Build a preview-only business launch pack with checkpoints before public or financial actions.",
        "allowed_autonomy_lanes": SAFE_DEFAULT_LANES,
        "hard_blocked_lanes": DEFAULT_HARD_BLOCKED_LANES,
        "steps": [
            {
                "step_id": "research_options",
                "title": "Research business options",
                "lane": "research",
                "classification": "safe_autonomous",
                "description": "Generate and compare business options.",
            },
            {
                "step_id": "draft_brand_options",
                "title": "Draft brand options",
                "lane": "creation",
                "classification": "safe_autonomous",
                "description": "Draft names, offers, positioning and launch assets.",
            },
            {
                "step_id": "approve_business_choice",
                "title": "Approve selected business direction",
                "lane": "legal_action",
                "classification": "checkpoint_required",
                "description": "Pause before any public, legal, financial, or deployment commitment.",
            },
        ],
        "human_checkpoints": [
            {
                "checkpoint_id": "approve_business_direction",
                "title": "Approve business direction",
                "required_before": ["approve_business_choice"],
                "approval_required_actions": [
                    "publish",
                    "buy_domain",
                    "spend_money",
                    "create_legal_commitment",
                    "deploy_page",
                ],
            }
        ],
        "outputs": ["business_build_pack", "launch_checklist", "mission_receipt_preview"],
    },
}


def list_mission_templates() -> list[dict[str, Any]]:
    return [
        {
            "template_id": template["template_id"],
            "name": template["name"],
            "business_vertical": template["business_vertical"],
            "mission_goal": template["mission_goal"],
            "template_hash": template_hash(template["template_id"]),
        }
        for template in MISSION_TEMPLATE_REGISTRY.values()
    ]


MISSION_TEMPLATE_ALIASES = {
    "home_fixed_lead_campaign": "home_fixed_lead_campaign_v0",
    "home_fixed_quote_intake": "home_fixed_quote_intake_v0",
    "weekly_marketing_pack": "weekly_marketing_pack_v0",
    "generic_business_build_pack": "generic_business_build_pack_v0",
}


def get_mission_template(template_id: str) -> dict[str, Any]:
    template_id = MISSION_TEMPLATE_ALIASES.get(template_id, template_id)
    if template_id not in MISSION_TEMPLATE_REGISTRY:
        raise KeyError(f"Unknown mission template: {template_id}")

    template = deepcopy(MISSION_TEMPLATE_REGISTRY[template_id])
    template["template_hash"] = template_hash(template_id)
    return template


def template_hash(template_id: str) -> str:
    template = deepcopy(MISSION_TEMPLATE_REGISTRY[template_id])
    template.pop("template_hash", None)
    return stable_hash(template)


def template_to_contract_seed(
    template_id: str,
    *,
    business_id: str,
    creator_id: str,
    mission_goal_override: str | None = None,
) -> dict[str, Any]:
    template = get_mission_template(template_id)
    mission_goal = mission_goal_override or template["mission_goal"]

    seed = {
        "schema_version": "aion.mission_contract.seed.v0",
        "source_template_id": template_id,
        "source_template_hash": template["template_hash"],
        "mission_goal": mission_goal,
        "business_id": business_id,
        "creator_id": creator_id,
        "agent_mode": "checkpointed_autonomy",
        "allowed_autonomy_lanes": template["allowed_autonomy_lanes"],
        "hard_blocked_lanes": template["hard_blocked_lanes"],
        "human_checkpoints": template["human_checkpoints"],
        "approval_required_actions": sorted(
            {
                action
                for checkpoint in template["human_checkpoints"]
                for action in checkpoint.get("approval_required_actions", [])
            }
        ),
        "planned_steps": template["steps"],
        "expected_outputs": template["outputs"],
        "proof_required": True,
        "replay_required": True,
        "ets_enabled": True,
        "live_execution_enabled": False,
        "external_writes_enabled": False,
        "native_runtime_owner": "aion_core",
        "executor_name": "AION Pilot",
    }

    seed["contract_seed_hash"] = stable_hash(seed)
    return seed
