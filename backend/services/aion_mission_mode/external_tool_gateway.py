"""
AION Phase 20H.1 — External Tool Gateway

Locks:
- Governed capability registry.
- Tool modes: safe_internal, read_only_external, staged_external, approved_live_external.
- No raw model access to external tools.
- Unregistered tools blocked.
- Live tools require approved payload.
- Every allowed call emits deterministic tool_call_hash.
- Live external execution emits capability receipt envelope.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Literal


ToolMode = Literal[
    "safe_internal",
    "read_only_external",
    "staged_external",
    "approved_live_external",
]

VALID_TOOL_MODES = {
    "safe_internal",
    "read_only_external",
    "staged_external",
    "approved_live_external",
}

LIVE_EXTERNAL_MODES = {"approved_live_external"}

DEFAULT_PROVIDERS = {
    "internal": {"provider_type": "internal"},
    "domain_provider": {"provider_type": "domain"},
    "hosting_provider": {"provider_type": "hosting"},
    "vercel": {"provider_type": "deployment"},
    "meta": {"provider_type": "marketing"},
    "google": {"provider_type": "search_profile"},
    "email_provider": {"provider_type": "email"},
    "whatsapp_provider": {"provider_type": "messaging"},
    "payment_provider": {"provider_type": "payment"},
    "booking_provider": {"provider_type": "booking"},
    "crm_provider": {"provider_type": "crm"},
}

DEFAULT_CAPABILITIES = {
    "generate_copy": {
        "provider": "internal",
        "tool_mode": "safe_internal",
        "risk_level": "low",
        "requires_payload_approval": False,
    },
    "create_site_files": {
        "provider": "internal",
        "tool_mode": "safe_internal",
        "risk_level": "low",
        "requires_payload_approval": False,
    },
    "run_local_build": {
        "provider": "internal",
        "tool_mode": "safe_internal",
        "risk_level": "low",
        "requires_payload_approval": False,
    },
    "browser_search": {
        "provider": "google",
        "tool_mode": "read_only_external",
        "risk_level": "medium",
        "requires_payload_approval": False,
    },
    "domain_availability_check": {
        "provider": "domain_provider",
        "tool_mode": "read_only_external",
        "risk_level": "medium",
        "requires_payload_approval": False,
    },
    "prepare_domain_purchase": {
        "provider": "domain_provider",
        "tool_mode": "staged_external",
        "risk_level": "high",
        "requires_payload_approval": False,
    },
    "prepare_vercel_deploy": {
        "provider": "vercel",
        "tool_mode": "staged_external",
        "risk_level": "high",
        "requires_payload_approval": False,
    },
    "prepare_facebook_post": {
        "provider": "meta",
        "tool_mode": "staged_external",
        "risk_level": "high",
        "requires_payload_approval": False,
    },
    "buy_domain": {
        "provider": "domain_provider",
        "tool_mode": "approved_live_external",
        "risk_level": "critical",
        "requires_payload_approval": True,
    },
    "deploy_to_vercel": {
        "provider": "vercel",
        "tool_mode": "approved_live_external",
        "risk_level": "critical",
        "requires_payload_approval": True,
    },
    "publish_facebook_post": {
        "provider": "meta",
        "tool_mode": "approved_live_external",
        "risk_level": "critical",
        "requires_payload_approval": True,
    },
    "send_email": {
        "provider": "email_provider",
        "tool_mode": "approved_live_external",
        "risk_level": "critical",
        "requires_payload_approval": True,
    },
    "send_whatsapp_message": {
        "provider": "whatsapp_provider",
        "tool_mode": "approved_live_external",
        "risk_level": "critical",
        "requires_payload_approval": True,
    },
    "start_ad_campaign": {
        "provider": "meta",
        "tool_mode": "approved_live_external",
        "risk_level": "critical",
        "requires_payload_approval": True,
    },
    "take_payment": {
        "provider": "payment_provider",
        "tool_mode": "approved_live_external",
        "risk_level": "critical",
        "requires_payload_approval": True,
    },
    "create_booking": {
        "provider": "booking_provider",
        "tool_mode": "approved_live_external",
        "risk_level": "critical",
        "requires_payload_approval": True,
    },
    "mutate_provider_account": {
        "provider": "internal",
        "tool_mode": "approved_live_external",
        "risk_level": "critical",
        "requires_payload_approval": True,
    },
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def validate_tool_mode(tool_mode: str) -> ToolMode:
    if tool_mode not in VALID_TOOL_MODES:
        raise ValueError(f"Unknown tool mode: {tool_mode}")
    return tool_mode  # type: ignore[return-value]


def create_capability_registry(
    *,
    registry_id: str = "aion_external_tool_gateway_v0",
    providers: dict[str, Any] | None = None,
    capabilities: dict[str, Any] | None = None,
) -> dict[str, Any]:
    provider_map = providers or DEFAULT_PROVIDERS
    capability_map = capabilities or DEFAULT_CAPABILITIES

    for capability_name, capability in capability_map.items():
        validate_tool_mode(capability["tool_mode"])
        if capability["provider"] not in provider_map:
            raise ValueError(f"Capability {capability_name} references unknown provider {capability['provider']}")

    result = {
        "schema_version": "aion.external_tool_gateway.registry.v0",
        "registry_id": registry_id,
        "providers": provider_map,
        "capabilities": capability_map,
        "capability_count": len(capability_map),
        "provider_count": len(provider_map),
        "registry_hash": "",
    }
    result["registry_hash"] = _hash({k: v for k, v in result.items() if k != "registry_hash"})
    return result


def get_capability(
    *,
    registry: dict[str, Any],
    tool_name: str,
) -> dict[str, Any] | None:
    capability = registry["capabilities"].get(tool_name)
    if not capability:
        return None
    return {
        "tool_name": tool_name,
        **capability,
    }


def create_tool_call_request(
    *,
    mission_id: str,
    mission_run_id: str,
    step_id: str,
    tool_name: str,
    requested_by: str,
    payload: dict[str, Any],
    approved_payload_hash: str | None = None,
    approval_hash: str | None = None,
    approval_expires_at: int | None = None,
) -> dict[str, Any]:
    result = {
        "schema_version": "aion.external_tool_gateway.request.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "step_id": step_id,
        "tool_name": tool_name,
        "requested_by": requested_by,
        "payload": payload,
        "payload_hash": _hash(payload),
        "approved_payload_hash": approved_payload_hash,
        "approval_hash": approval_hash,
        "approval_expires_at": approval_expires_at,
        "request_hash": "",
    }
    result["request_hash"] = _hash({k: v for k, v in result.items() if k != "request_hash"})
    return result


def evaluate_tool_call(
    *,
    registry: dict[str, Any],
    request: dict[str, Any],
    evaluation_time: int,
    caller: str = "aion_pilot",
) -> dict[str, Any]:
    tool_name = request["tool_name"]
    capability = get_capability(registry=registry, tool_name=tool_name)

    reasons: list[str] = []
    allowed = True

    if caller == "model":
        allowed = False
        reasons.append("raw_model_tool_access_blocked")

    if capability is None:
        allowed = False
        reasons.append("unregistered_tool_blocked")
        tool_mode = None
        provider = None
        risk_level = "unknown"
        requires_payload_approval = True
    else:
        tool_mode = capability["tool_mode"]
        provider = capability["provider"]
        risk_level = capability["risk_level"]
        requires_payload_approval = bool(capability["requires_payload_approval"])

    if capability is not None and tool_mode in LIVE_EXTERNAL_MODES:
        if not request.get("approved_payload_hash"):
            allowed = False
            reasons.append("missing_approved_payload_hash")
        if not request.get("approval_hash"):
            allowed = False
            reasons.append("missing_approval_hash")
        if request.get("approval_expires_at") is None:
            allowed = False
            reasons.append("missing_approval_expiry")
        elif int(evaluation_time) > int(request["approval_expires_at"]):
            allowed = False
            reasons.append("approval_expired")
        if request.get("approved_payload_hash") and request["approved_payload_hash"] != request["payload_hash"]:
            allowed = False
            reasons.append("payload_hash_mismatch")

    result = {
        "schema_version": "aion.external_tool_gateway.evaluation.v0",
        "mission_id": request["mission_id"],
        "mission_run_id": request["mission_run_id"],
        "step_id": request["step_id"],
        "tool_name": tool_name,
        "caller": caller,
        "provider": provider,
        "tool_mode": tool_mode,
        "risk_level": risk_level,
        "requires_payload_approval": requires_payload_approval,
        "payload_hash": request["payload_hash"],
        "approved_payload_hash": request.get("approved_payload_hash"),
        "approval_hash": request.get("approval_hash"),
        "evaluation_time": int(evaluation_time),
        "allowed": allowed,
        "gateway_state": "allowed" if allowed else "blocked",
        "reasons": reasons,
        "tool_call_hash": "",
    }
    result["tool_call_hash"] = _hash({k: v for k, v in result.items() if k != "tool_call_hash"})
    return result


def create_capability_receipt(
    *,
    evaluation: dict[str, Any],
    provider_response: dict[str, Any] | None = None,
    before_state_hash: str | None = None,
    after_state_hash: str | None = None,
    evidence_hashes: list[str] | None = None,
    rollback_available: bool = False,
    rollback_instructions: str | None = None,
) -> dict[str, Any]:
    if not evaluation["allowed"]:
        raise ValueError("Cannot create capability receipt for blocked tool call")

    result = {
        "schema_version": "aion.external_tool_gateway.capability_receipt.v0",
        "mission_id": evaluation["mission_id"],
        "mission_run_id": evaluation["mission_run_id"],
        "step_id": evaluation["step_id"],
        "tool_name": evaluation["tool_name"],
        "provider": evaluation["provider"],
        "tool_mode": evaluation["tool_mode"],
        "requested_payload_hash": evaluation["payload_hash"],
        "executed_payload_hash": evaluation["payload_hash"],
        "tool_call_hash": evaluation["tool_call_hash"],
        "before_state_hash": before_state_hash,
        "after_state_hash": after_state_hash,
        "evidence_hashes": evidence_hashes or [],
        "provider_response_hash": _hash(provider_response or {}),
        "rollback_available": rollback_available,
        "rollback_instructions": rollback_instructions,
        "receipt_hash": "",
    }
    result["receipt_hash"] = _hash({k: v for k, v in result.items() if k != "receipt_hash"})
    return result


def gateway_summary(registry: dict[str, Any]) -> dict[str, Any]:
    modes: dict[str, int] = {mode: 0 for mode in sorted(VALID_TOOL_MODES)}
    for capability in registry["capabilities"].values():
        modes[capability["tool_mode"]] += 1

    result = {
        "schema_version": "aion.external_tool_gateway.summary.v0",
        "registry_id": registry["registry_id"],
        "registry_hash": registry["registry_hash"],
        "capability_count": registry["capability_count"],
        "provider_count": registry["provider_count"],
        "tool_mode_counts": modes,
        "summary_hash": "",
    }
    result["summary_hash"] = _hash({k: v for k, v in result.items() if k != "summary_hash"})
    return result
