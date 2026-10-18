from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


class PlanningArbiterError(ValueError):
    pass


class PlannerConsensusRejected(PlanningArbiterError):
    pass


class UnsupportedPlannerProvider(PlanningArbiterError):
    pass


ALLOWED_PROVIDERS: Set[str] = {
    "gemma_local",
    "openai_frontier",
    "mock_planner",
}

HIGH_RISK_ACTION_TYPES: Set[str] = {
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

HUMAN_TASK_ACTION_TYPES: Set[str] = {
    "create_real_facebook_account",
    "create_google_business_profile",
    "verify_phone_number",
    "upload_identity_document",
    "answer_verification_call",
    "take_real_job_photos",
    "sign_legal_document",
    "provide_provider_access",
}

FORBIDDEN_FIELDS: Set[str] = {
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


def _canonical_hash(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _scan_for_forbidden_fields(node: Any) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in FORBIDDEN_FIELDS:
                raise PlannerConsensusRejected(f"forbidden_planner_field_detected:{key}")
            _scan_for_forbidden_fields(value)
    elif isinstance(node, list):
        for item in node:
            _scan_for_forbidden_fields(item)


def _normalise_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _step_key(step: Dict[str, Any]) -> str:
    action = _normalise_text(step.get("action_type") or step.get("suggested_action_type"))
    title = _normalise_text(step.get("title"))
    if action and action != "unknown":
        return action
    return title


def _effective_control_for_action(action_type: str, fallback: str = "autonomous") -> str:
    if action_type in HUMAN_TASK_ACTION_TYPES:
        return "human_task_required"
    if action_type in HIGH_RISK_ACTION_TYPES:
        return "human_approval_required"
    return fallback or "autonomous"


def _normalise_step(step: Dict[str, Any], provider: str, index: int) -> Dict[str, Any]:
    action_type = str(step.get("action_type") or step.get("suggested_action_type") or "unknown")
    suggested_lane = str(step.get("lane") or step.get("suggested_lane") or "autonomous")
    effective_control = _effective_control_for_action(action_type, suggested_lane)

    return {
        "step_id": str(step.get("step_id") or f"{provider}_step_{index:03d}"),
        "title": str(step.get("title") or f"Step {index}"),
        "description": str(step.get("description") or ""),
        "action_type": action_type,
        "provider_hint": str(step.get("provider_hint") or step.get("provider") or "none"),
        "estimated_cost": round(float(step.get("estimated_cost") or 0.0), 2),
        "planner_suggested_lane": suggested_lane,
        "aion_effective_control": effective_control,
        "planner_labels_advisory_only": True,
    }


def normalise_planner_proposal(provider: str, proposal: Dict[str, Any]) -> Dict[str, Any]:
    if provider not in ALLOWED_PROVIDERS:
        raise UnsupportedPlannerProvider(f"unsupported_planner_provider:{provider}")

    _scan_for_forbidden_fields(proposal)

    raw_steps = proposal.get("steps") or proposal.get("suggested_steps") or []
    if not isinstance(raw_steps, list):
        raise PlannerConsensusRejected("planner_steps_must_be_list")

    steps = [_normalise_step(step, provider, i + 1) for i, step in enumerate(raw_steps)]

    normalised = {
        "provider": provider,
        "title": str(proposal.get("title") or proposal.get("plan_title") or "Planner Proposal"),
        "steps": steps,
        "planner_output_type": "structured_plan_proposal_only",
        "model_may_execute": False,
        "model_may_call_raw_tools": False,
        "model_may_mutate_runtime": False,
        "requires_aion_compilation": True,
        "planner_labels_advisory_only": True,
    }
    normalised["proposal_hash"] = _canonical_hash(normalised)
    return normalised


def compare_step_sets(primary: Dict[str, Any], secondary: Dict[str, Any]) -> Dict[str, Any]:
    primary_keys = {_step_key(step) for step in primary["steps"]}
    secondary_keys = {_step_key(step) for step in secondary["steps"]}

    shared = sorted(primary_keys & secondary_keys)
    primary_only = sorted(primary_keys - secondary_keys)
    secondary_only = sorted(secondary_keys - primary_keys)

    union_count = len(primary_keys | secondary_keys)
    similarity = 1.0 if union_count == 0 else round(len(shared) / union_count, 4)

    result = {
        "primary_provider": primary["provider"],
        "secondary_provider": secondary["provider"],
        "shared_step_keys": shared,
        "primary_only_step_keys": primary_only,
        "secondary_only_step_keys": secondary_only,
        "jaccard_similarity": similarity,
    }
    result["comparison_hash"] = _canonical_hash(result)
    return result


def merge_planner_proposals(
    mission_id: str,
    business_id: str,
    proposals: Sequence[Dict[str, Any]],
    *,
    min_similarity: float = 0.2,
    max_merged_steps: int = 80,
) -> Dict[str, Any]:
    if len(proposals) < 1:
        raise PlannerConsensusRejected("at_least_one_proposal_required")

    providers = [p["provider"] for p in proposals]
    if len(set(providers)) != len(providers):
        raise PlannerConsensusRejected("duplicate_provider_proposals_rejected")

    comparisons: List[Dict[str, Any]] = []
    if len(proposals) > 1:
        anchor = proposals[0]
        for other in proposals[1:]:
            comparison = compare_step_sets(anchor, other)
            comparisons.append(comparison)
            if comparison["jaccard_similarity"] < min_similarity:
                raise PlannerConsensusRejected("planner_similarity_below_threshold")

    merged_by_key: Dict[str, Dict[str, Any]] = {}
    source_map: Dict[str, List[str]] = {}

    for proposal in proposals:
        for step in proposal["steps"]:
            key = _step_key(step)
            if key not in merged_by_key:
                merged_by_key[key] = dict(step)
                source_map[key] = []
            source_map[key].append(proposal["provider"])

            current = merged_by_key[key]
            current_control = current.get("aion_effective_control", "autonomous")
            new_control = step.get("aion_effective_control", "autonomous")

            strictness = {
                "autonomous": 0,
                "human_approval_required": 1,
                "human_task_required": 2,
                "blocked": 3,
            }

            if strictness.get(new_control, 0) > strictness.get(current_control, 0):
                current["aion_effective_control"] = new_control

            current["estimated_cost"] = round(
                max(float(current.get("estimated_cost") or 0.0), float(step.get("estimated_cost") or 0.0)),
                2,
            )

    merged_steps = list(merged_by_key.values())
    if len(merged_steps) > max_merged_steps:
        raise PlannerConsensusRejected("merged_step_count_exceeds_limit")

    for idx, step in enumerate(merged_steps, start=1):
        key = _step_key(step)
        step["step_id"] = f"arb_step_{idx:03d}"
        step["source_planners"] = sorted(source_map[key])
        step["consensus_support_count"] = len(set(source_map[key]))

    output = {
        "mission_id": mission_id,
        "business_id": business_id,
        "arbiter_output_type": "deterministic_multi_model_plan_proposal",
        "providers": sorted(providers),
        "proposal_hashes": sorted(p["proposal_hash"] for p in proposals),
        "comparisons": comparisons,
        "steps": merged_steps,
        "planner_labels_advisory_only": True,
        "model_may_execute": False,
        "model_may_call_raw_tools": False,
        "model_may_mutate_runtime": False,
        "requires_aion_compilation": True,
        "compiled_contract_state": "requires_plan_matrix_review",
        "must_pass_plan_approval_matrix": True,
        "must_pass_approval_lattice": True,
        "must_pass_autonomy_budget": True,
        "must_pass_expiry_revocation": True,
        "must_pass_external_tool_gateway": True,
        "live_external_side_effects_allowed": False,
    }
    output["arbiter_hash"] = _canonical_hash(output)
    return output


def compile_arbiter_output_to_contract(arbiter_output: Dict[str, Any]) -> Dict[str, Any]:
    if arbiter_output.get("arbiter_output_type") != "deterministic_multi_model_plan_proposal":
        raise PlannerConsensusRejected("invalid_arbiter_output_type")

    contract = {
        "mission_id": arbiter_output["mission_id"],
        "business_id": arbiter_output["business_id"],
        "arbiter_hash": arbiter_output["arbiter_hash"],
        "steps": arbiter_output["steps"],
        "compiled_contract_state": "requires_plan_matrix_review",
        "must_pass_plan_approval_matrix": True,
        "must_pass_approval_lattice": True,
        "must_pass_autonomy_budget": True,
        "must_pass_expiry_revocation": True,
        "must_pass_external_tool_gateway": True,
        "live_external_side_effects_allowed": False,
    }
    contract["contract_hash"] = _canonical_hash(contract)
    return contract
