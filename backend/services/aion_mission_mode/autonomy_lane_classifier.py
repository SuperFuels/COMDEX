"""
AION Phase 20D Autonomy Lane Classifier v0

Contract:
- Deterministic only.
- No LLM calls.
- No live tools.
- No external writes.
- Planner/model labels are advisory only.
- Classifier owns final lane + execution decision.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
import re
from typing import Any


LANES = {
    "research",
    "creation",
    "internal_ops",
    "external_action",
    "financial_action",
    "legal_action",
    "deployment_action",
    "memory_mutation",
}

DECISIONS = {
    "safe_autonomous",
    "checkpoint_required",
    "blocked",
    "forbidden",
}

SAFE_RESEARCH_ACTIONS = {
    "research_service_angle",
    "analyse_local_market",
    "summarise_context",
    "compare_options",
    "review_business_focus",
    "research_options",
}

SAFE_CREATION_ACTIONS = {
    "draft_offer",
    "draft_facebook_advert",
    "draft_landing_page_copy",
    "draft_lead_form_questions",
    "draft_intake_questions",
    "draft_posts",
    "draft_brand_options",
    "create_campaign_pack",
}

SAFE_INTERNAL_OPS_ACTIONS = {
    "create_workflow_preview",
    "create_agentmap_preview",
    "create_quote_intake_preview",
    "create_boardroom_summary",
    "create_quote_preview",
    "stage_quote",
    "index_lead",
    "run_local_test",
    "create_internal_draft",
}

EXTERNAL_ACTIONS = {
    "publish_advert",
    "publish_post",
    "send_customer_message",
    "send_message",
    "send_email",
    "send_whatsapp",
    "contact_customer",
    "dispatch_worker",
}

FINANCIAL_ACTIONS = {
    "spend_money",
    "take_payment",
    "capture_payment",
    "create_escrow",
    "buy_domain",
    "charge_card",
    "trigger_payout",
}

LEGAL_ACTIONS = {
    "create_legal_commitment",
    "sign_contract",
    "accept_terms",
    "submit_legal_form",
    "approve_business_choice",
}

DEPLOYMENT_ACTIONS = {
    "deploy_live_page",
    "deploy_page",
    "deploy_production",
    "publish_website",
    "push_to_production",
}

MEMORY_MUTATION_ACTIONS = {
    "mutate_business_memory",
    "write_live_reputation",
    "save_business_rule",
    "promote_memory_to_business",
    "write_long_term_memory",
}

FORBIDDEN_ACTIONS = {
    "send_whatsapp_live",
    "send_email_live",
    "capture_payment_live",
    "create_booking_live",
    "deploy_production_live",
    "write_live_reputation",
    "raw_terminal_exec",
    "raw_shell_exec",
    "raw_browser_submit",
    "raw_database_write",
}

BLOCKED_PAYLOAD_TOKENS = {
    "send_whatsapp_live",
    "send_email_live",
    "capture_payment_live",
    "create_booking_live",
    "deploy_production_live",
    "write_live_reputation",
    "external_writes_enabled=true",
    "live_execution_enabled=true",
    "payment_live=true",
    "booking_live=true",
    "escrow_live=true",
}


SAFE_STEP_TOP_LEVEL_KEYS = {
    "action",
    "action_type",
    "artifact_type",
    "classification",
    "decision",
    "description",
    "id",
    "lane",
    "preferred_sub_container",
    "produces_artifact",
    "requires_checkpoint",
    "step_id",
    "title",
}

DANGEROUS_SCHEMA_KEYS = {
    "booking_live",
    "browser_submit",
    "capture_payment_live",
    "charge_card",
    "database_write",
    "deploy_production_live",
    "escrow_live",
    "external_writes_enabled",
    "live_booking_enabled",
    "live_chain_write_enabled",
    "live_deployment_enabled",
    "live_execution_enabled",
    "live_payment_enabled",
    "live_reputation_mutation_enabled",
    "message_send",
    "payment_live",
    "raw_browser_submit",
    "raw_database_write",
    "raw_shell_exec",
    "raw_terminal_exec",
    "send_email_live",
    "send_whatsapp_live",
    "tool_call",
    "write_live_reputation",
}

BATCH_BLOCKING_DECISIONS = {"blocked", "forbidden"}


LIVE_FLAG_KEYS = {
    "external_writes_enabled",
    "live_execution_enabled",
    "payment_live",
    "booking_live",
    "escrow_live",
    "live_payment_enabled",
    "live_booking_enabled",
    "live_deployment_enabled",
    "live_reputation_mutation_enabled",
    "live_chain_write_enabled",
}


@dataclass(frozen=True)
class LaneClassification:
    action_type: str
    lane: str
    decision: str
    requires_checkpoint: bool
    safe_autonomous: bool
    reason: str
    planner_lane: str | None = None
    planner_decision: str | None = None
    classifier_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["classifier_hash"] = self.hash_without_self(payload)
        return payload

    @staticmethod
    def hash_without_self(payload: dict[str, Any]) -> str:
        clean = dict(payload)
        clean.pop("classifier_hash", None)
        encoded = json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return sha256(encoded.encode("utf-8")).hexdigest()


def _slug(value: Any) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace(".", "_")
    )


def _payload_text(step: dict[str, Any]) -> str:
    return json.dumps(step, sort_keys=True, separators=(",", ":"), ensure_ascii=False).lower()


def _contains_live_flag(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_slug = normalize_payload_key(key)
            if key_slug in LIVE_FLAG_KEYS and item is True:
                return key_slug
            nested = _contains_live_flag(item)
            if nested:
                return nested

    if isinstance(value, list):
        for item in value:
            nested = _contains_live_flag(item)
            if nested:
                return nested

    return None


def _contains_blocked_payload_token(step: dict[str, Any]) -> str | None:
    live_flag = _contains_live_flag(step)
    if live_flag:
        return live_flag

    text = _payload_text(step)
    compact = text.replace(" ", "")
    colon_compact = compact.replace('":true', '=true').replace(':true', '=true')

    for token in sorted(BLOCKED_PAYLOAD_TOKENS):
        token_lower = token.lower()
        if token_lower in text or token_lower in compact or token_lower in colon_compact:
            return token

    return None


def classify_action_type(action_type: str) -> tuple[str, str, str]:
    action = _slug(action_type)

    if action in FORBIDDEN_ACTIONS:
        return "external_action", "forbidden", "Forbidden live/raw action attempted."

    if action in MEMORY_MUTATION_ACTIONS:
        return "memory_mutation", "checkpoint_required", "Memory mutation requires governed checkpoint."

    if action in DEPLOYMENT_ACTIONS:
        return "deployment_action", "checkpoint_required", "Deployment requires checkpoint approval."

    if action in LEGAL_ACTIONS:
        return "legal_action", "checkpoint_required", "Legal commitment requires checkpoint approval."

    if action in FINANCIAL_ACTIONS:
        return "financial_action", "checkpoint_required", "Financial action requires checkpoint approval."

    if action in EXTERNAL_ACTIONS:
        return "external_action", "checkpoint_required", "External action requires checkpoint approval."

    if action in SAFE_RESEARCH_ACTIONS:
        return "research", "safe_autonomous", "Safe research action."

    if action in SAFE_CREATION_ACTIONS:
        return "creation", "safe_autonomous", "Safe creation/drafting action."

    if action in SAFE_INTERNAL_OPS_ACTIONS:
        return "internal_ops", "safe_autonomous", "Safe internal preview operation."

    return "internal_ops", "blocked", "Unknown action blocked until explicitly classified."




def normalize_payload_key(key: Any) -> str:
    """Canonicalise payload keys before forbidden-registry checks."""
    value = str(key or "")
    value = value.lower().replace("-", "_")
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_")


def _find_forbidden_schema_key(value: Any, path: str = "") -> str | None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_slug = normalize_payload_key(key)
            current_path = f"{path}.{key_slug}" if path else key_slug

            if key_slug in DANGEROUS_SCHEMA_KEYS:
                return current_path

            nested = _find_forbidden_schema_key(item, current_path)
            if nested:
                return nested

    if isinstance(value, list):
        for index, item in enumerate(value):
            nested = _find_forbidden_schema_key(item, f"{path}[{index}]")
            if nested:
                return nested

    return None


def _find_unknown_safe_step_key(step: dict[str, Any]) -> str | None:
    for key in step.keys():
        key_slug = normalize_payload_key(key)
        if key_slug not in SAFE_STEP_TOP_LEVEL_KEYS:
            return key_slug
    return None


def _blocked_result(
    *,
    action_type: str,
    lane: str,
    decision: str,
    reason: str,
    planner_lane: Any = None,
    planner_decision: Any = None,
) -> dict[str, Any]:
    result = LaneClassification(
        action_type=action_type,
        lane=lane,
        decision=decision,
        requires_checkpoint=True,
        safe_autonomous=False,
        reason=reason,
        planner_lane=str(planner_lane) if planner_lane is not None else None,
        planner_decision=str(planner_decision) if planner_decision is not None else None,
    )
    return result.to_dict()


def classify_mission_step(step: dict[str, Any]) -> dict[str, Any]:
    action_type = _slug(step.get("action_type") or step.get("step_id") or step.get("action") or "")
    planner_lane = step.get("lane")
    planner_decision = step.get("decision") or step.get("classification")

    forbidden_schema_key = _find_forbidden_schema_key(step)
    if forbidden_schema_key:
        return _blocked_result(
            action_type=action_type,
            lane="external_action",
            decision="forbidden",
            reason=f"forbidden_payload_shape:{forbidden_schema_key}",
            planner_lane=planner_lane,
            planner_decision=planner_decision,
        )

    blocked_token = _contains_blocked_payload_token(step)
    if blocked_token:
        return _blocked_result(
            action_type=action_type,
            lane="external_action",
            decision="forbidden",
            reason=f"Blocked payload token detected: {blocked_token}",
            planner_lane=planner_lane,
            planner_decision=planner_decision,
        )

    lane, decision, reason = classify_action_type(action_type)

    if decision == "safe_autonomous":
        unknown_key = _find_unknown_safe_step_key(step)
        if unknown_key:
            return _blocked_result(
                action_type=action_type,
                lane=lane,
                decision="blocked",
                reason=f"unapproved_parameter:{unknown_key}",
                planner_lane=planner_lane,
                planner_decision=planner_decision,
            )

    result = LaneClassification(
        action_type=action_type,
        lane=lane,
        decision=decision,
        requires_checkpoint=decision in {"checkpoint_required", "blocked", "forbidden"},
        safe_autonomous=decision == "safe_autonomous",
        reason=reason,
        planner_lane=str(planner_lane) if planner_lane is not None else None,
        planner_decision=str(planner_decision) if planner_decision is not None else None,
    )
    return result.to_dict()


def calculate_classifier_run_hash(step_outputs: list[dict[str, Any]]) -> str:
    hasher = sha256()

    for step in sorted(step_outputs, key=lambda item: str(item.get("action_type", ""))):
        serialized = json.dumps(
            step,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        hasher.update(serialized.encode("utf-8"))

    return f"sha256:{hasher.hexdigest()}"


def classify_mission_steps(steps: list[dict[str, Any]]) -> dict[str, Any]:
    classifications = [classify_mission_step(step) for step in steps]

    blocked_count = sum(1 for item in classifications if item["decision"] == "blocked")
    forbidden_count = sum(1 for item in classifications if item["decision"] == "forbidden")
    batch_valid = blocked_count == 0 and forbidden_count == 0

    mission_runtime_state = "ready_for_runtime"
    if forbidden_count:
        mission_runtime_state = "blocked"
    elif blocked_count:
        mission_runtime_state = "waiting_human_review"

    summary = {
        "schema_version": "aion.autonomy_lane_classifier.v0",
        "classifier": "deterministic_system_classifier",
        "planner_labels_are_advisory_only": True,
        "atomic_batch_isolation": True,
        "batch_valid": batch_valid,
        "runtime_mount_allowed": batch_valid,
        "mission_runtime_state": mission_runtime_state,
        "total_steps": len(classifications),
        "safe_autonomous_count": sum(1 for item in classifications if item["decision"] == "safe_autonomous"),
        "checkpoint_required_count": sum(1 for item in classifications if item["decision"] == "checkpoint_required"),
        "blocked_count": blocked_count,
        "forbidden_count": forbidden_count,
        "classifications": classifications,
    }

    summary["classifier_run_hash"] = calculate_classifier_run_hash(classifications)

    return summary


def verify_runtime_queue_hash(
    *,
    classifier_result: dict[str, Any],
    runtime_classifications: list[dict[str, Any]],
) -> dict[str, Any]:
    expected_hash = str(classifier_result.get("classifier_run_hash") or "")
    runtime_hash = calculate_classifier_run_hash(runtime_classifications)

    ok = expected_hash == runtime_hash

    return {
        "ok": ok,
        "expected_classifier_run_hash": expected_hash,
        "runtime_classifier_run_hash": runtime_hash,
        "runtime_mount_allowed": ok and bool(classifier_result.get("runtime_mount_allowed")),
        "mission_runtime_state": "ready_for_runtime" if ok and bool(classifier_result.get("runtime_mount_allowed")) else "blocked",
        "trace_event": None if ok else "classifier_runtime_hash_mismatch",
        "boardroom_alert": None if ok else "Classifier/runtime queue hash mismatch. Runtime mount refused.",
    }

