"""Shared authority contract for AION's legacy and canonical cognitive engines.

The contract deliberately separates proposals from execution authority.  Legacy
engines may enrich a proposal, but they cannot claim that an action happened or
that a lesson is true without an execution adapter and a verified outcome.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Callable, Mapping


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        if isinstance(value, Mapping):
            return {str(k): _json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_json_safe(v) for v in value]
        return repr(value)


def canonical_hash(value: Any) -> str:
    payload = json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class CognitiveActionContract:
    objective: str
    goal_id: str = "unassigned"
    action_type: str = "investigate"
    risk_tier: str = "low"
    approval_policy: str = "proposal_only"
    requires_consent: bool = False
    consent_granted: bool = False
    capability_decision: str = "unknown"
    expected_outcome: str = ""
    verification_plan: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    reversible: bool = True
    rollback_plan: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | str) -> "CognitiveActionContract":
        if isinstance(value, str):
            value = {"objective": value}
        capability = value.get("capability_decision") or {}
        if isinstance(capability, Mapping):
            capability = capability.get("decision") or capability.get("action") or "unknown"
        return cls(
            objective=str(value.get("objective") or value.get("goal") or value.get("what") or "").strip(),
            goal_id=str(value.get("goal_id") or "unassigned"),
            action_type=str(value.get("action_type") or value.get("type") or "investigate"),
            risk_tier=str(value.get("risk_tier") or "low").lower(),
            approval_policy=str(value.get("approval_policy") or "proposal_only"),
            requires_consent=bool(value.get("requires_consent")),
            consent_granted=bool(value.get("consent_granted")),
            capability_decision=str(capability),
            expected_outcome=str(value.get("expected_outcome") or ""),
            verification_plan=tuple(str(x) for x in value.get("verification_plan") or ()),
            evidence_refs=tuple(str(x) for x in value.get("evidence_refs") or ()),
            assumptions=tuple(str(x) for x in value.get("assumptions") or ()),
            reversible=bool(value.get("reversible", True)),
            rollback_plan=str(value.get("rollback_plan") or ""),
            metadata=dict(value.get("metadata") or {}),
        )

    def proposal(self, **extra: Any) -> dict[str, Any]:
        body = {
            "schema_version": "aion.governed_cognitive_action.v1",
            "goal_id": self.goal_id,
            "objective": self.objective,
            "action_type": self.action_type,
            "risk_tier": self.risk_tier,
            "approval_policy": self.approval_policy,
            "requires_consent": self.requires_consent,
            "consent_granted": self.consent_granted,
            "capability_decision": self.capability_decision,
            "expected_outcome": self.expected_outcome,
            "verification_plan": list(self.verification_plan),
            "evidence_refs": list(self.evidence_refs),
            "assumptions": list(self.assumptions),
            "reversible": self.reversible,
            "rollback_plan": self.rollback_plan,
            "proposal_only": True,
            "created_at": utc_now(),
            **_json_safe(extra),
        }
        body["contract_id"] = "cog_" + canonical_hash(body)[:20]
        return body


def authority_check(contract: CognitiveActionContract, *, adapter: Any = None) -> dict[str, Any]:
    reasons: list[str] = []
    if not contract.objective:
        reasons.append("objective_missing")
    if contract.capability_decision in {"learn_then_execute", "clarify", "blocked", "unknown"}:
        reasons.append("capability_not_ready")
    if contract.requires_consent and not contract.consent_granted:
        reasons.append("required_consent_missing")
    if contract.risk_tier in {"high", "critical"} and contract.approval_policy != "human_approved":
        reasons.append("high_risk_human_approval_missing")
    elif contract.approval_policy not in {"autonomous_allowed", "human_approved"}:
        reasons.append("execution_authority_missing")
    if not callable(adapter):
        reasons.append("verified_execution_adapter_missing")
    return {
        "authorized": not reasons,
        "reasons": reasons,
        "checked_at": utc_now(),
        "proposal_only": True,
    }


def execute_with_authority(
    contract: CognitiveActionContract,
    adapter: Callable[[dict[str, Any]], Mapping[str, Any]] | None,
) -> dict[str, Any]:
    check = authority_check(contract, adapter=adapter)
    proposal = contract.proposal(authority_check=check)
    if not check["authorized"]:
        return {**proposal, "status": "not_executed", "authority_check": check}
    result = dict(adapter(proposal))
    verified = result.get("verified") is True and bool(result.get("outcome_hash"))
    return {
        **proposal,
        "proposal_only": False,
        "status": "verified" if verified else "unverified_outcome",
        "executed_at": utc_now(),
        "authority_check": check,
        "result": _json_safe(result),
        "verified": verified,
    }

