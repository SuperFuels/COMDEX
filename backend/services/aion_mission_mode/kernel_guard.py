"""
AION Phase 20V — Deterministic System Interceptor / Kernel Guard

Contract:
- Deterministic execution firewall.
- Treat planner and classifier labels as advisory until verified.
- Validate proposed tool payloads against hard restricted-action registry.
- Override unsafe safe_autonomous decisions to checkpoint_required or forbidden.
- No live tools.
- No external writes.
- No payments, bookings, escrow, deployment, messaging, or reputation mutation.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
import re
from typing import Any

from backend.services.aion_mission_mode.autonomy_lane_classifier import (
    classify_mission_step,
    normalize_payload_key,
)


RESTRICTED_ACTION_REGISTRY: dict[str, str] = {
    "send_email": "external_action",
    "send_email_live": "external_action",
    "send_whatsapp": "external_action",
    "send_whatsapp_live": "external_action",
    "send_customer_message": "external_action",
    "publish_advert": "external_action",
    "publish_post": "external_action",
    "post_social": "external_action",
    "create_booking": "external_action",
    "create_booking_live": "external_action",
    "dispatch_worker": "external_action",
    "take_payment": "financial_action",
    "capture_payment": "financial_action",
    "capture_payment_live": "financial_action",
    "create_escrow": "financial_action",
    "release_escrow": "financial_action",
    "spend_money": "financial_action",
    "buy_domain": "financial_action",
    "create_legal_commitment": "legal_action",
    "sign_contract": "legal_action",
    "deploy_live_page": "deployment_action",
    "deploy_production_live": "deployment_action",
    "raw_terminal_exec": "deployment_action",
    "write_live_reputation": "memory_mutation",
    "mutate_business_memory": "memory_mutation",
}

FORBIDDEN_RUNTIME_FLAGS = {
    "live_execution_enabled",
    "external_writes_enabled",
    "payment_enabled",
    "booking_enabled",
    "deployment_enabled",
    "reputation_mutation_enabled",
    "chain_write_enabled",
    "raw_terminal_exec",
}


@dataclass(frozen=True)
class KernelGuardDecision:
    ok: bool
    action_type: str
    original_decision: str
    final_decision: str
    lane: str
    override_applied: bool
    runtime_mount_allowed: bool
    requires_checkpoint: bool
    reason: str
    guard_hash: str


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def canonicalise_action_type(value: Any) -> str:
    """Canonicalise action_type before restricted registry lookup."""
    text = str(value or "")
    text = text.lower().replace("-", "_")
    text = re.sub(r"[\s\u200b-\u200d\ufeff]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def _slug(value: Any) -> str:
    return canonicalise_action_type(value)


def _scan_for_runtime_flags(value: Any, path: str = "$") -> str | None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalised = normalize_payload_key(key)
            current_path = f"{path}.{normalised}"
            if normalised in FORBIDDEN_RUNTIME_FLAGS and item is True:
                return current_path
            nested = _scan_for_runtime_flags(item, current_path)
            if nested:
                return nested

    if isinstance(value, list):
        for index, item in enumerate(value):
            nested = _scan_for_runtime_flags(item, f"{path}[{index}]")
            if nested:
                return nested

    return None


def inspect_kernel_payload(step: dict[str, Any]) -> KernelGuardDecision:
    action_type = _slug(step.get("action_type") or step.get("action") or "")
    classifier = classify_mission_step(step)

    original_decision = str(step.get("decision") or classifier.get("decision") or "blocked")
    classifier_decision = str(classifier.get("decision") or "blocked")
    classifier_lane = str(classifier.get("lane") or "internal_ops")

    flag_path = _scan_for_runtime_flags(step)
    if flag_path:
        payload = {
            "action_type": action_type,
            "original_decision": original_decision,
            "final_decision": "forbidden",
            "lane": classifier_lane,
            "reason": f"kernel_forbidden_runtime_flag:{flag_path}",
        }
        return KernelGuardDecision(
            ok=False,
            action_type=action_type,
            original_decision=original_decision,
            final_decision="forbidden",
            lane=classifier_lane,
            override_applied=True,
            runtime_mount_allowed=False,
            requires_checkpoint=True,
            reason=payload["reason"],
            guard_hash=_hash(payload),
        )

    if action_type in RESTRICTED_ACTION_REGISTRY:
        lane = RESTRICTED_ACTION_REGISTRY[action_type]
        final = "checkpoint_required"

        payload = {
            "action_type": action_type,
            "original_decision": original_decision,
            "final_decision": final,
            "lane": lane,
            "reason": "kernel_restricted_action_override",
        }

        return KernelGuardDecision(
            ok=True,
            action_type=action_type,
            original_decision=original_decision,
            final_decision=final,
            lane=lane,
            override_applied=original_decision != final or classifier_decision != final,
            runtime_mount_allowed=False,
            requires_checkpoint=True,
            reason=payload["reason"],
            guard_hash=_hash(payload),
        )

    if classifier_decision in {"blocked", "forbidden"}:
        payload = {
            "action_type": action_type,
            "original_decision": original_decision,
            "final_decision": classifier_decision,
            "lane": classifier_lane,
            "reason": f"kernel_classifier_{classifier_decision}",
        }

        return KernelGuardDecision(
            ok=False,
            action_type=action_type,
            original_decision=original_decision,
            final_decision=classifier_decision,
            lane=classifier_lane,
            override_applied=original_decision != classifier_decision,
            runtime_mount_allowed=False,
            requires_checkpoint=True,
            reason=payload["reason"],
            guard_hash=_hash(payload),
        )

    payload = {
        "action_type": action_type,
        "original_decision": original_decision,
        "final_decision": "safe_autonomous",
        "lane": classifier_lane,
        "reason": "kernel_safe_verified",
    }

    return KernelGuardDecision(
        ok=True,
        action_type=action_type,
        original_decision=original_decision,
        final_decision="safe_autonomous",
        lane=classifier_lane,
        override_applied=original_decision != "safe_autonomous",
        runtime_mount_allowed=True,
        requires_checkpoint=False,
        reason=payload["reason"],
        guard_hash=_hash(payload),
    )


def inspect_kernel_batch(steps: list[dict[str, Any]]) -> dict[str, Any]:
    decisions = [asdict(inspect_kernel_payload(step)) for step in steps]
    mount_allowed = all(item["runtime_mount_allowed"] for item in decisions)

    blocked_or_checkpointed = [
        item for item in decisions
        if item["final_decision"] in {"blocked", "forbidden", "checkpoint_required"}
    ]

    result = {
        "ok": mount_allowed,
        "runtime_mount_allowed": mount_allowed,
        "mission_runtime_state": "ready_for_runtime" if mount_allowed else "waiting_human_review",
        "decisions": decisions,
        "blocked_or_checkpointed_count": len(blocked_or_checkpointed),
        "kernel_guard_run_hash": "",
        "boardroom_alerts": [
            {
                "type": "kernel_guard_override",
                "action_type": item["action_type"],
                "decision": item["final_decision"],
                "reason": item["reason"],
            }
            for item in decisions
            if item["override_applied"] or item["final_decision"] in {"blocked", "forbidden", "checkpoint_required"}
        ],
    }

    result["kernel_guard_run_hash"] = "sha256:" + _hash({
        "decisions": decisions,
        "runtime_mount_allowed": mount_allowed,
        "mission_runtime_state": result["mission_runtime_state"],
    })

    return result
