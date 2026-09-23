from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from backend.services.aion_mission_mode.pilot_artifact_builder_runtime import (
    PilotArtifactBuilderRuntime,
)


class PilotSafeStepExecutionBlocked(ValueError):
    pass


LIVE_OR_RISKY_ACTIONS = {
    "publish_advert",
    "publish_facebook_post",
    "send_customer_message",
    "send_email_campaign",
    "send_whatsapp_message",
    "start_ad_campaign",
    "spend_money",
    "buy_domain",
    "pay_for_hosting",
    "deploy_live_page",
    "deploy_to_production",
    "connect_dns",
    "create_booking",
    "take_payment",
    "create_escrow",
    "dispatch_worker",
    "submit_legal_document",
    "submit_identity_document",
    "live_customer_message",
    "write_reputation",
    "mutate_memory",
}

HUMAN_ONLY_ACTIONS = {
    "create_real_facebook_account",
    "create_google_business_profile",
    "verify_phone_number",
    "upload_identity_document",
    "answer_verification_call",
    "take_real_job_photos",
    "sign_legal_document",
    "provide_provider_access",
}

SAFE_DECISIONS = {
    "safe_internal",
    "safe_autonomous",
    "autonomous",
}

SAFE_LANES = {
    "research",
    "creation",
    "internal_ops",
    "safe_internal",
}


def canonical_hash(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _slug(value: Any) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", str(value or "").strip().lower().replace("-", "_")).strip("_")


def _safe_artifact_name(step: Dict[str, Any], index: int) -> str:
    step_id = _slug(step.get("step_id") or step.get("id") or f"step_{index + 1:02d}")
    action = _slug(step.get("action_type") or "safe_step")
    name = f"{step_id or 'step'}_{action or 'safe_step'}.md"
    return name[:120]


def assert_safe_internal_step(step: Dict[str, Any]) -> Dict[str, Any]:
    action_type = _slug(step.get("action_type") or "")
    decision = _slug(
        step.get("decision")
        or step.get("aion_effective_control")
        or step.get("default_control")
        or ""
    )
    lane = _slug(step.get("lane") or step.get("node_type") or "")

    violations = []

    if action_type in LIVE_OR_RISKY_ACTIONS:
        violations.append("live_or_risky_action_requires_approval")

    if action_type in HUMAN_ONLY_ACTIONS:
        violations.append("human_only_action_requires_human_task")

    if bool(step.get("requires_checkpoint")) is True:
        violations.append("checkpoint_required")

    if bool(step.get("external_side_effect")) is True:
        violations.append("external_side_effect_not_allowed")

    if bool(step.get("live_external_side_effects_allowed")) is True:
        violations.append("live_external_side_effect_flag_not_allowed")

    if decision and decision not in SAFE_DECISIONS:
        violations.append(f"unsafe_decision:{decision}")

    if lane and lane not in SAFE_LANES and str(step.get("node_type") or "") != "mission_plan_safe_step":
        violations.append(f"unsafe_lane:{lane}")

    if violations:
        raise PilotSafeStepExecutionBlocked(",".join(violations))

    return {
        "action_type": action_type or "safe_internal_work",
        "decision": decision or "safe_internal",
        "lane": lane or "safe_internal",
        "violations": [],
    }


def assert_tool_execution_item_allows_safe_step(tool_execution_item: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not tool_execution_item:
        return {
            "tool_queue_bound": False,
            "department_id": None,
            "department_capability": None,
            "gateway_tool_name": None,
            "local_tool_id": None,
            "tool_mode": None,
            "tool_execution_item_hash": None,
        }

    status = str(tool_execution_item.get("status") or "").strip()
    tool_mode = str(tool_execution_item.get("tool_mode") or "").strip()
    live_external_side_effect = tool_execution_item.get("live_external_side_effect") is True
    execution_allowed = tool_execution_item.get("execution_allowed") is True
    live_execution_allowed = tool_execution_item.get("live_execution_allowed") is True

    violations = []

    if status not in {"ready", "staged"}:
        violations.append(f"tool_item_status_not_runnable:{status or 'missing'}")

    if tool_mode not in {"safe_internal", "read_only_external", "staged_external"}:
        violations.append(f"tool_mode_not_safe_for_step_executor:{tool_mode or 'missing'}")

    if execution_allowed is not True:
        violations.append("tool_execution_not_allowed_by_gateway")

    if live_execution_allowed is True:
        violations.append("live_execution_flag_not_allowed")

    if live_external_side_effect is True:
        violations.append("live_external_side_effect_not_allowed")

    if violations:
        raise PilotSafeStepExecutionBlocked(",".join(violations))

    return {
        "tool_queue_bound": True,
        "department_id": tool_execution_item.get("department_id"),
        "department_capability": tool_execution_item.get("department_capability"),
        "gateway_tool_name": tool_execution_item.get("gateway_tool_name"),
        "local_tool_id": tool_execution_item.get("local_tool_id"),
        "tool_mode": tool_mode,
        "tool_execution_item_hash": tool_execution_item.get("tool_execution_item_hash"),
    }


def build_safe_step_prompt(
    *,
    user_goal: str,
    step: Dict[str, Any],
    business_context: Dict[str, Any],
    mission_plan: Dict[str, Any],
) -> str:
    return "\n".join(
        [
            "You are AION Pilot safe internal executor.",
            "",
            "Execute the current safe internal mission step and produce the actual usable draft output.",
            "Do not claim to publish, send, spend, deploy, book, escrow, mutate provider state, mutate live memory, or write reputation.",
            "Return only the work product for the user, with clear sections and next review points.",
            "",
            "User goal:",
            str(user_goal or ""),
            "",
            "Current safe step:",
            json.dumps(step, sort_keys=True, ensure_ascii=False, indent=2),
            "",
            "Business / brand / marketing context:",
            json.dumps(business_context, sort_keys=True, ensure_ascii=False, indent=2)[:12000],
            "",
            "Context use rule:",
            "Use business_context, business_context_mission_map, brand_foundation_state, marketing_form, marketing_summary, draft_steps and approval_stages as authoritative context. Do not invent generic business assumptions when context is present.",
            "",
            "Clarification rule:",
            "If the current step asks to clarify target audience, offer, tone, service area, channels or objective, first extract those fields from supplied context. Ask the user only for fields genuinely missing from all supplied context.",
            "",
            "Mission plan context:",
            json.dumps(mission_plan, sort_keys=True, ensure_ascii=False, indent=2)[:8000],
        ]
    )


def execute_pilot_safe_step(
    *,
    container_root: str,
    business_id: str,
    mission_id: str,
    mission_run_id: str,
    user_goal: str,
    step: Dict[str, Any],
    step_index: int = 0,
    business_context: Optional[Dict[str, Any]] = None,
    mission_plan: Optional[Dict[str, Any]] = None,
    assistant_fn: Optional[Callable[[str], str]] = None,
    tool_execution_item: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    tool_context = assert_tool_execution_item_allows_safe_step(tool_execution_item)

    if tool_execution_item and not step:
        step = {
            "step_id": tool_execution_item.get("task_id") or "tool_queue_step",
            "title": tool_execution_item.get("title") or "Tool queue safe step",
            "action_type": tool_execution_item.get("department_capability") or "safe_internal_work",
            "decision": "safe_internal",
            "lane": "safe_internal",
            "requires_checkpoint": False,
            "live_external_side_effects_allowed": False,
            "external_side_effect": False,
        }

    safety = assert_safe_internal_step(step)

    prompt = build_safe_step_prompt(
        user_goal=user_goal,
        step=step,
        business_context={
            **(business_context or {}),
            "tool_execution_item": tool_execution_item or {},
            "tool_execution_context": tool_context,
        },
        mission_plan=mission_plan or {},
    )

    output_text = ""
    if assistant_fn is not None:
        output_text = str(assistant_fn(prompt) or "").strip()

    if not output_text:
        output_text = "\n".join(
            [
                "Safe internal step execution did not receive generated content from the assistant provider.",
                "",
                "The step was validated as safe internal work, but no work product was returned.",
                "",
                "No live external side effects were performed.",
            ]
        )

    step_id = str(step.get("step_id") or step.get("id") or f"step_{step_index + 1:02d}")
    title = str(step.get("title") or step.get("action_type") or "Safe internal step")

    contract = PilotArtifactBuilderRuntime.build_artifact_contract(
        business_id=str(business_id or "home-fixed"),
        mission_id=str(mission_id or "pilot_mission"),
        mission_run_id=str(mission_run_id or "pilot_run"),
        step_id=step_id,
        artifact_type="markdown",
        artifact_name=_safe_artifact_name(step, step_index),
        requested_by="aion_pilot_safe_step_executor",
        status="draft_preview",
    )

    artifact_card = PilotArtifactBuilderRuntime.create_draft_artifact(
        container_root=container_root,
        contract=contract,
        title=title,
        content=output_text,
        metadata={
            "user_goal": user_goal,
            "step_index": step_index,
            "action_type": safety["action_type"],
            "decision": safety["decision"],
            "department_id": tool_context.get("department_id"),
            "department_capability": tool_context.get("department_capability"),
            "gateway_tool_name": tool_context.get("gateway_tool_name"),
            "local_tool_id": tool_context.get("local_tool_id"),
            "tool_mode": tool_context.get("tool_mode"),
            "tool_execution_item_hash": tool_context.get("tool_execution_item_hash"),
            "tool_queue_bound": tool_context.get("tool_queue_bound") is True,
        },
    )

    result = {
        "payload_type": "aion_pilot_safe_step_execution",
        "status": "completed_draft_preview",
        "business_id": business_id,
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "step_index": step_index,
        "step_id": step_id,
        "title": title,
        "action_type": safety["action_type"],
        "decision": safety["decision"],
        "output_text": output_text,
        "artifact_card": artifact_card,
        "artifact_hash": artifact_card["artifact_hash"],
        "receipt_hash": artifact_card["artifact_receipt_hash"],
        "live_external_side_effects_allowed": False,
        "live_external_side_effects_performed": False,
        "raw_tool_execution_allowed": False,
        "tool_queue_bound": tool_context.get("tool_queue_bound") is True,
        "department_id": tool_context.get("department_id"),
        "department_capability": tool_context.get("department_capability"),
        "gateway_tool_name": tool_context.get("gateway_tool_name"),
        "local_tool_id": tool_context.get("local_tool_id"),
        "tool_mode": tool_context.get("tool_mode"),
        "tool_execution_item_hash": tool_context.get("tool_execution_item_hash"),
        "tool_execution_item": tool_execution_item or None,
    }
    result["execution_hash"] = canonical_hash(result)
    return result
