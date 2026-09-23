import hashlib
import json
from typing import Any, Dict, List


class PlannerAdapterError(Exception):
    pass


class PlannerBypassViolation(Exception):
    pass


ALLOWED_PROVIDERS = {
    "gemma_local",
    "openai_frontier",
    "mock_planner",
}

FORBIDDEN_PLAN_KEYS = {
    "execute_now",
    "raw_tool_call",
    "tool_call",
    "browser_submit",
    "payment_submit",
    "deploy_now",
    "publish_now",
    "send_now",
    "create_booking_now",
    "mutate_memory_now",
    "write_reputation_now",
}

FORBIDDEN_ACTION_TYPES = {
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

SAFE_DEFAULT_CONTROL = "autonomous"
APPROVAL_REQUIRED_CONTROL = "human_approval_required"
HUMAN_TASK_CONTROL = "human_task_required"


def canonical_hash(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def assert_supported_provider(provider: str) -> None:
    if provider not in ALLOWED_PROVIDERS:
        raise PlannerAdapterError(f"Unsupported planner provider: {provider}")


def assert_no_forbidden_keys(obj: Any, path: str = "root") -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in FORBIDDEN_PLAN_KEYS:
                raise PlannerBypassViolation(f"Forbidden planner key at {path}.{key}")
            assert_no_forbidden_keys(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            assert_no_forbidden_keys(value, f"{path}[{index}]")


def normalise_step(raw: Dict[str, Any], index: int) -> Dict[str, Any]:
    step_id = str(raw.get("step_id") or f"step_{index + 1:03d}")
    title = str(raw.get("title") or f"Step {index + 1}")
    description = str(raw.get("description") or "")
    action_type = str(raw.get("action_type") or "internal_planning")
    lane = str(raw.get("lane") or "creation")
    risk_level = str(raw.get("risk_level") or "low")
    provider = str(raw.get("provider") or "internal")
    estimated_cost = float(raw.get("estimated_cost") or 0.0)

    external_side_effect = bool(raw.get("external_side_effect", False))
    payload_required_later = bool(raw.get("payload_required_later", False))

    if action_type in FORBIDDEN_ACTION_TYPES:
        default_control = APPROVAL_REQUIRED_CONTROL
        external_side_effect = True
        payload_required_later = True
        risk_level = "high"
    elif lane in {"external", "financial", "legal", "deployment", "publishing", "messaging", "memory"}:
        default_control = APPROVAL_REQUIRED_CONTROL
        payload_required_later = True
        external_side_effect = True
        risk_level = "high"
    elif action_type in {
        "create_real_facebook_account",
        "create_google_business_profile",
        "verify_phone_number",
        "upload_identity_document",
        "answer_verification_call",
        "take_real_job_photos",
        "sign_legal_document",
        "provide_provider_access",
    }:
        default_control = HUMAN_TASK_CONTROL
        risk_level = "medium"
    else:
        default_control = SAFE_DEFAULT_CONTROL

    step = {
        "step_id": step_id,
        "title": title,
        "description": description,
        "action_type": action_type,
        "lane": lane,
        "risk_level": risk_level,
        "provider": provider,
        "estimated_cost": round(estimated_cost, 2),
        "external_side_effect": external_side_effect,
        "payload_required_later": payload_required_later,
        "planner_label_advisory_only": True,
        "default_control": default_control,
        "compiled_by_aion": True,
    }
    step["step_hash"] = canonical_hash(step)
    return step


def compile_structured_plan_proposal(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    provider: str,
    user_goal: str,
    raw_model_plan: Dict[str, Any],
) -> Dict[str, Any]:
    assert_supported_provider(provider)
    assert_no_forbidden_keys(raw_model_plan)

    raw_steps = raw_model_plan.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise PlannerAdapterError("Planner output must include a non-empty steps list.")

    steps = [normalise_step(step, index) for index, step in enumerate(raw_steps)]

    proposal = {
        "schema_version": "aion.phase20k.llm_planner_adapter.v1",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "planner_provider": provider,
        "user_goal": user_goal,
        "plan_title": str(raw_model_plan.get("plan_title") or "AION Mission Plan"),
        "planner_output_type": "structured_plan_proposal_only",
        "planner_labels_advisory_only": True,
        "model_may_execute": False,
        "model_may_call_raw_tools": False,
        "model_may_mutate_runtime": False,
        "requires_aion_compilation": True,
        "steps": steps,
    }

    proposal["proposal_hash"] = canonical_hash(proposal)
    return proposal


def compile_mission_contract_from_plan(proposal: Dict[str, Any]) -> Dict[str, Any]:
    if proposal.get("model_may_execute") is not False:
        raise PlannerBypassViolation("Planner proposal attempted to enable model execution.")

    if proposal.get("model_may_call_raw_tools") is not False:
        raise PlannerBypassViolation("Planner proposal attempted raw tool access.")

    if proposal.get("model_may_mutate_runtime") is not False:
        raise PlannerBypassViolation("Planner proposal attempted runtime mutation.")

    contract = {
        "schema_version": "aion.phase20k.compiled_mission_contract.v1",
        "mission_id": proposal["mission_id"],
        "mission_run_id": proposal["mission_run_id"],
        "business_id": proposal["business_id"],
        "source_proposal_hash": proposal["proposal_hash"],
        "planner_provider": proposal["planner_provider"],
        "steps": proposal["steps"],
        "compiled_contract_state": "requires_plan_matrix_review",
        "must_pass_plan_approval_matrix": True,
        "must_pass_approval_lattice": True,
        "must_pass_autonomy_budget": True,
        "must_pass_expiry_revocation": True,
        "must_pass_external_tool_gateway": True,
        "live_external_side_effects_allowed": False,
    }

    contract["mission_contract_hash"] = canonical_hash(contract)
    return contract
