# backend/modules/aion_gateway/exceptions.py
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


EXCEPTION_CONTRACT_VERSION = "aion.exception_recovery.v0.1"


SUPPORTED_EXCEPTION_TYPES = {
    "provider_late",
    "provider_cancelled",
    "missing_evidence",
    "quote_changed",
    "budget_exceeded",
    "approval_delayed",
    "unsafe_request_blocked",
    "customer_dispute",
    "proof_verification_failed",
    "settlement_readiness_blocked",
}


SUPPORTED_RECOVERY_ACTIONS = {
    "reschedule",
    "backup_provider",
    "pause",
    "cancel",
    "escalate",
    "request_missing_evidence",
    "revise_quote",
    "recommend_refund",
}


DEFAULT_ACTIONS_BY_EXCEPTION_TYPE: Dict[str, List[str]] = {
    "provider_late": ["reschedule", "escalate"],
    "provider_cancelled": ["backup_provider", "reschedule", "cancel"],
    "missing_evidence": ["request_missing_evidence", "pause"],
    "quote_changed": ["revise_quote", "escalate"],
    "budget_exceeded": ["revise_quote", "cancel", "escalate"],
    "approval_delayed": ["pause", "escalate"],
    "unsafe_request_blocked": ["cancel", "escalate"],
    "customer_dispute": ["pause", "escalate", "recommend_refund"],
    "proof_verification_failed": ["pause", "request_missing_evidence", "escalate"],
    "settlement_readiness_blocked": ["pause", "recommend_refund", "escalate"],
}


def _stable_hash(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FulfilmentException:
    exception_id: str
    exception_type: str
    business_id: str
    job_id: str
    severity: str = "medium"
    source: str = "aion_gateway"
    summary: str = ""
    detected_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    evidence_refs: List[str] = field(default_factory=list)
    blocked_reasons: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        data = asdict(self)
        data["contract_version"] = EXCEPTION_CONTRACT_VERSION
        data["exception_hash"] = _stable_hash({k: v for k, v in data.items() if k != "exception_hash"})
        return data


@dataclass(frozen=True)
class ExceptionRecoveryAction:
    action_type: str
    label: str
    requires_human_review: bool = True
    autonomous_execution_allowed: bool = False
    would_execute_workflow: bool = False
    would_create_booking: bool = False
    would_move_money: bool = False
    would_create_payment: bool = False
    would_create_escrow: bool = False
    would_send_external_message: bool = False
    blocked_reasons: List[str] = field(default_factory=list)

    def to_payload(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExceptionRecoveryPreview:
    ok: bool
    status: str
    exception: Dict[str, Any]
    recovery_actions: List[Dict[str, Any]]
    human_review_required: bool = True
    autonomous_execution_allowed: bool = False
    would_execute_workflow: bool = False
    would_create_booking: bool = False
    would_move_money: bool = False
    would_create_payment: bool = False
    would_create_escrow: bool = False
    would_send_external_message: bool = False
    blocked_reasons: List[str] = field(default_factory=list)
    exception_state_hash: str = ""

    def to_payload(self) -> Dict[str, Any]:
        data = asdict(self)
        data["exception_state_hash"] = _stable_hash(
            {k: v for k, v in data.items() if k != "exception_state_hash"}
        )
        return data


def _action_label(action_type: str) -> str:
    return action_type.replace("_", " ").title()


def build_exception_recovery_preview(
    *,
    exception_type: str,
    business_id: str,
    job_id: str,
    summary: str = "",
    severity: str = "medium",
    source: str = "aion_gateway",
    evidence_refs: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    requested_actions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    blocked_reasons: List[str] = []

    etype = str(exception_type or "").strip()
    bid = str(business_id or "").strip()
    jid = str(job_id or "").strip()

    if etype not in SUPPORTED_EXCEPTION_TYPES:
        blocked_reasons.append("unsupported_exception_type")
    if not bid:
        blocked_reasons.append("missing_business_id")
    if not jid:
        blocked_reasons.append("missing_job_id")

    candidate_actions = list(requested_actions or DEFAULT_ACTIONS_BY_EXCEPTION_TYPE.get(etype, []))
    recovery_actions: List[Dict[str, Any]] = []

    for action_type in candidate_actions:
        atype = str(action_type or "").strip()
        action_blocked: List[str] = []

        if atype not in SUPPORTED_RECOVERY_ACTIONS:
            action_blocked.append("unsupported_recovery_action")

        action_blocked.extend(
            [
                "human_review_required",
                "autonomous_recovery_execution_disabled",
                "would_execute_workflow_false",
                "would_create_booking_false",
                "would_move_money_false",
                "would_create_payment_false",
                "would_create_escrow_false",
                "would_send_external_message_false",
            ]
        )

        recovery_actions.append(
            ExceptionRecoveryAction(
                action_type=atype,
                label=_action_label(atype),
                requires_human_review=True,
                autonomous_execution_allowed=False,
                would_execute_workflow=False,
                would_create_booking=False,
                would_move_money=False,
                would_create_payment=False,
                would_create_escrow=False,
                would_send_external_message=False,
                blocked_reasons=action_blocked,
            ).to_payload()
        )

    exc = FulfilmentException(
        exception_id=_stable_hash(
            {
                "exception_type": etype,
                "business_id": bid,
                "job_id": jid,
                "summary": summary,
                "severity": severity,
                "source": source,
                "evidence_refs": list(evidence_refs or []),
                "metadata": dict(metadata or {}),
            }
        )[:24],
        exception_type=etype,
        business_id=bid,
        job_id=jid,
        severity=str(severity or "medium"),
        source=str(source or "aion_gateway"),
        summary=str(summary or ""),
        evidence_refs=list(evidence_refs or []),
        blocked_reasons=list(blocked_reasons),
        metadata=dict(metadata or {}),
    ).to_payload()

    preview = ExceptionRecoveryPreview(
        ok=(not blocked_reasons),
        status=("blocked" if blocked_reasons else "preview_ready"),
        exception=exc,
        recovery_actions=recovery_actions,
        human_review_required=True,
        autonomous_execution_allowed=False,
        would_execute_workflow=False,
        would_create_booking=False,
        would_move_money=False,
        would_create_payment=False,
        would_create_escrow=False,
        would_send_external_message=False,
        blocked_reasons=blocked_reasons,
    ).to_payload()

    return preview


def build_exception_state_for_machine_trace(preview: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compact machine-trace compatible exception state.

    This does not expose a public route. It only gives the existing machine trace
    layer a deterministic state object it can later embed.
    """
    exception = preview.get("exception") if isinstance(preview.get("exception"), dict) else {}
    actions = preview.get("recovery_actions") if isinstance(preview.get("recovery_actions"), list) else []

    state = {
        "contract_version": EXCEPTION_CONTRACT_VERSION,
        "status": str(preview.get("status") or "unknown"),
        "exception_id": str(exception.get("exception_id") or ""),
        "exception_type": str(exception.get("exception_type") or ""),
        "business_id": str(exception.get("business_id") or ""),
        "job_id": str(exception.get("job_id") or ""),
        "severity": str(exception.get("severity") or ""),
        "summary": str(exception.get("summary") or ""),
        "recovery_action_types": [
            str(a.get("action_type") or "")
            for a in actions
            if isinstance(a, dict)
        ],
        "human_review_required": bool(preview.get("human_review_required", True)),
        "autonomous_execution_allowed": False,
        "blocked_reasons": list(preview.get("blocked_reasons") or []),
        "exception_state_hash": str(preview.get("exception_state_hash") or ""),
    }
    state["machine_trace_exception_hash"] = _stable_hash(
        {k: v for k, v in state.items() if k != "machine_trace_exception_hash"}
    )
    return state


def example_home_fixed_exception_preview() -> Dict[str, Any]:
    return build_exception_recovery_preview(
        exception_type="provider_late",
        business_id="home_fixed",
        job_id="hf_job_preview_001",
        summary="Provider is running late for a Home Fixed repair appointment.",
        severity="medium",
        source="agent_channel",
        evidence_refs=["message_ref_provider_eta_001"],
        metadata={"vertical_key": "home_repair"},
    )
