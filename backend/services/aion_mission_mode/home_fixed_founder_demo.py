from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List


def canonical_hash(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


ALWAYS_APPROVAL_ACTIONS = {
    "buy_domain",
    "deploy_to_production",
    "publish_facebook_post",
    "start_ad_campaign",
    "send_email_campaign",
    "send_whatsapp_message",
    "take_payment",
    "create_booking",
}

HUMAN_TASK_ACTIONS = {
    "create_real_facebook_account",
    "create_google_business_profile",
    "verify_phone_number",
    "upload_identity_document",
    "take_real_job_photos",
    "provide_provider_access",
}


def build_home_fixed_founder_demo_plan(
    *,
    business_id: str = "home_fixed",
    mission_id: str = "home_fixed_founder_demo",
    mission_run_id: str = "run_demo_001",
) -> Dict[str, Any]:
    steps = [
        {
            "step_id": "step_001",
            "title": "Draft Home Fixed roofing/pergola offer",
            "action_type": "draft_offer",
            "lane": "safe_internal",
            "control_mode": "autonomous",
            "estimated_cost": 0.0,
        },
        {
            "step_id": "step_002",
            "title": "Draft landing page copy",
            "action_type": "draft_landing_page",
            "lane": "safe_internal",
            "control_mode": "autonomous",
            "estimated_cost": 0.0,
        },
        {
            "step_id": "step_003",
            "title": "Draft Facebook post and advert copy",
            "action_type": "draft_advert",
            "lane": "safe_internal",
            "control_mode": "autonomous",
            "estimated_cost": 0.0,
        },
        {
            "step_id": "step_004",
            "title": "Prepare local website project",
            "action_type": "create_local_website_project",
            "lane": "safe_internal",
            "control_mode": "autonomous",
            "estimated_cost": 0.0,
        },
        {
            "step_id": "step_005",
            "title": "Prepare Vercel preview",
            "action_type": "prepare_vercel_preview",
            "lane": "staged_external",
            "control_mode": "human_approval_required",
            "estimated_cost": 0.0,
        },
        {
            "step_id": "step_006",
            "title": "Prepare domain checkout preview",
            "action_type": "prepare_domain_checkout_preview",
            "lane": "staged_external",
            "control_mode": "human_approval_required",
            "estimated_cost": 12.0,
        },
        {
            "step_id": "step_007",
            "title": "Purchase domain",
            "action_type": "buy_domain",
            "lane": "approved_live_external",
            "control_mode": "human_approval_required",
            "estimated_cost": 12.0,
        },
        {
            "step_id": "step_008",
            "title": "Deploy production website",
            "action_type": "deploy_to_production",
            "lane": "approved_live_external",
            "control_mode": "human_approval_required",
            "estimated_cost": 0.0,
        },
        {
            "step_id": "step_009",
            "title": "Create/verify Facebook and Google profiles",
            "action_type": "create_real_facebook_account",
            "lane": "human_external",
            "control_mode": "human_task_required",
            "estimated_cost": 0.0,
        },
        {
            "step_id": "step_010",
            "title": "Publish first public post",
            "action_type": "publish_facebook_post",
            "lane": "approved_live_external",
            "control_mode": "human_approval_required",
            "estimated_cost": 0.0,
        },
        {
            "step_id": "step_011",
            "title": "Start ad campaign",
            "action_type": "start_ad_campaign",
            "lane": "approved_live_external",
            "control_mode": "human_approval_required",
            "estimated_cost": 25.0,
        },
        {
            "step_id": "step_012",
            "title": "Emit proof, replay and ETS preview",
            "action_type": "emit_demo_proof",
            "lane": "safe_internal",
            "control_mode": "autonomous",
            "estimated_cost": 0.0,
        },
    ]

    plan = {
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "vertical": "home_repair_roofing_pergola",
        "demo_name": "Home Fixed Founder Demo",
        "demo_goal": "Build and market a Home Fixed roofing/pergola lead generation campaign without unapproved external side effects.",
        "steps": steps,
        "live_payment_created": False,
        "live_booking_created": False,
        "live_escrow_created": False,
        "live_external_message_sent": False,
        "live_production_deploy_created": False,
        "live_reputation_mutated": False,
    }
    plan["plan_hash"] = canonical_hash(plan)
    return plan


def classify_demo_step(step: Dict[str, Any]) -> Dict[str, Any]:
    action_type = step["action_type"]
    reasons: List[str] = []

    if action_type in ALWAYS_APPROVAL_ACTIONS:
        effective_mode = "human_approval_required"
        reasons.append("always_approval_action")
    elif action_type in HUMAN_TASK_ACTIONS:
        effective_mode = "human_task_required"
        reasons.append("human_task_required")
    else:
        effective_mode = step.get("control_mode", "autonomous")
        reasons.append("safe_internal_or_staged_preview")

    blocked_live_execution = effective_mode in {"human_approval_required", "human_task_required"}

    result = {
        "step_id": step["step_id"],
        "action_type": action_type,
        "lane": step["lane"],
        "requested_control_mode": step["control_mode"],
        "effective_control_mode": effective_mode,
        "blocked_live_execution": blocked_live_execution,
        "reasons": reasons,
    }
    result["classification_hash"] = canonical_hash(result)
    return result


def build_demo_safety_matrix(plan: Dict[str, Any]) -> Dict[str, Any]:
    classifications = [classify_demo_step(step) for step in plan["steps"]]
    blocked = [c for c in classifications if c["blocked_live_execution"]]
    autonomous = [c for c in classifications if c["effective_control_mode"] == "autonomous"]

    matrix = {
        "mission_id": plan["mission_id"],
        "mission_run_id": plan["mission_run_id"],
        "business_id": plan["business_id"],
        "plan_hash": plan["plan_hash"],
        "classifications": classifications,
        "autonomous_step_count": len(autonomous),
        "blocked_or_gated_step_count": len(blocked),
        "approval_required_count": sum(1 for c in classifications if c["effective_control_mode"] == "human_approval_required"),
        "human_task_required_count": sum(1 for c in classifications if c["effective_control_mode"] == "human_task_required"),
        "external_side_effects_allowed_without_approval": False,
    }
    matrix["demo_safety_matrix_hash"] = canonical_hash(matrix)
    return matrix


def build_founder_demo_outputs(plan: Dict[str, Any], matrix: Dict[str, Any]) -> Dict[str, Any]:
    outputs = {
        "offer_draft": "Roofing, pergola and outdoor living repairs for Home Fixed customers across Almería and Murcia.",
        "landing_page_draft": {
            "headline": "Roofing & Outdoor Living Repairs",
            "subheadline": "Pergola roofs, leaks, repairs and practical upgrades by Home Fixed.",
            "cta": "Message Home Fixed for a quote preview.",
        },
        "ad_draft": {
            "headline": "Need a roof or pergola fixed?",
            "body": "Home Fixed can help with pergola roofs, leaks, outdoor repairs and villa upgrades. Message for a quote preview.",
        },
        "website_project_preview": {
            "created_locally": True,
            "production_deployed": False,
        },
        "vercel_preview": {
            "prepared": True,
            "production_deployed": False,
            "requires_approval_before_deploy": True,
        },
        "domain_checkout_preview": {
            "prepared": True,
            "domain_purchased": False,
            "requires_exact_payload_approval": True,
        },
        "public_post_preview": {
            "prepared": True,
            "published": False,
            "requires_approval_before_publish": True,
        },
        "ad_campaign_preview": {
            "prepared": True,
            "started": False,
            "requires_approval_before_spend": True,
        },
    }
    outputs["outputs_hash"] = canonical_hash(outputs)

    receipt = {
        "mission_id": plan["mission_id"],
        "mission_run_id": plan["mission_run_id"],
        "business_id": plan["business_id"],
        "plan_hash": plan["plan_hash"],
        "demo_safety_matrix_hash": matrix["demo_safety_matrix_hash"],
        "outputs_hash": outputs["outputs_hash"],
        "proves_autonomous_safe_work": True,
        "proves_controlled_external_execution": True,
        "no_unapproved_payment": True,
        "no_unapproved_deploy": True,
        "no_unapproved_publish": True,
        "no_unapproved_send": True,
        "no_unapproved_booking": True,
        "ets_preview_only": True,
    }
    receipt["founder_demo_receipt_hash"] = canonical_hash(receipt)

    return {
        "outputs": outputs,
        "receipt": receipt,
    }


def build_home_fixed_founder_demo_contract() -> Dict[str, Any]:
    plan = build_home_fixed_founder_demo_plan()
    matrix = build_demo_safety_matrix(plan)
    output_bundle = build_founder_demo_outputs(plan, matrix)

    contract = {
        "demo_contract_type": "home_fixed_founder_demo_v0",
        "mission_id": plan["mission_id"],
        "mission_run_id": plan["mission_run_id"],
        "business_id": plan["business_id"],
        "plan": plan,
        "safety_matrix": matrix,
        "outputs": output_bundle["outputs"],
        "receipt": output_bundle["receipt"],
        "boardroom_message": "AION completed safe work autonomously and stopped itself before doing anything risky.",
        "literal_safety_message": "AION stopped itself before doing anything risky.",
    }
    contract["founder_demo_contract_hash"] = canonical_hash(contract)
    return contract
