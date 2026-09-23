"""
AION Phase 20H.2 — Provider Context Isolation + Credential Vault Scoping

Locks:
- Provider execution contexts are mission/run/provider scoped.
- Credentials are represented by vault references only.
- Model-visible context never contains plaintext secrets.
- Cross-provider and cross-mission context reuse is blocked.
- Context mount emits deterministic context hashes.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any


SECRET_KEYS = {
    "password",
    "passwd",
    "secret",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "session_token",
    "cookie",
    "cookies",
    "authorization",
    "auth_header",
    "payment_token",
    "card_number",
    "cvv",
}


VALID_PROVIDERS = {
    "domain_provider",
    "hosting_provider",
    "vercel",
    "meta",
    "google",
    "email_provider",
    "whatsapp_provider",
    "payment_provider",
    "booking_provider",
    "crm_provider",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def validate_provider(provider: str) -> str:
    if provider not in VALID_PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}")
    return provider


def contains_secret_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).lower() in SECRET_KEYS:
                return True
            if contains_secret_key(nested):
                return True
    elif isinstance(value, list):
        return any(contains_secret_key(item) for item in value)
    return False


def redact_model_visible_state(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, nested in value.items():
            if str(key).lower() in SECRET_KEYS:
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_model_visible_state(nested)
        return redacted
    if isinstance(value, list):
        return [redact_model_visible_state(item) for item in value]
    return value


def contains_unredacted_secret_value(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).lower() in SECRET_KEYS:
                if nested != "[REDACTED]":
                    return True
            elif contains_unredacted_secret_value(nested):
                return True
    elif isinstance(value, list):
        return any(contains_unredacted_secret_value(item) for item in value)
    return False


def create_vault_reference(
    *,
    business_id: str,
    provider: str,
    credential_scope: str,
    vault_key_id: str,
) -> dict[str, Any]:
    validate_provider(provider)

    result = {
        "schema_version": "aion.provider_vault_reference.v0",
        "business_id": business_id,
        "provider": provider,
        "credential_scope": credential_scope,
        "vault_key_id": vault_key_id,
        "secret_material_exposed": False,
        "vault_reference_hash": "",
    }
    result["vault_reference_hash"] = _hash(
        {k: v for k, v in result.items() if k != "vault_reference_hash"}
    )
    return result


def create_provider_context(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    provider: str,
    tool_name: str,
    vault_reference: dict[str, Any],
    allowed_actions: list[str],
    context_claims: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_provider(provider)

    if vault_reference["provider"] != provider:
        raise ValueError("Vault reference provider mismatch")

    context_claims = context_claims or {}

    if contains_secret_key(context_claims):
        raise ValueError("Context claims contain raw secret-shaped fields")

    result = {
        "schema_version": "aion.provider_execution_context.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "provider": provider,
        "tool_name": tool_name,
        "vault_reference_hash": vault_reference["vault_reference_hash"],
        "credential_scope": vault_reference["credential_scope"],
        "allowed_actions": sorted(set(allowed_actions)),
        "context_claims": context_claims,
        "secret_material_exposed": False,
        "context_hash": "",
    }
    result["context_hash"] = _hash({k: v for k, v in result.items() if k != "context_hash"})
    return result


def create_model_visible_context(
    *,
    provider_context: dict[str, Any],
    page_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    page_state = page_state or {}
    safe_page_state = redact_model_visible_state(page_state)

    result = {
        "schema_version": "aion.model_visible_provider_context.v0",
        "mission_id": provider_context["mission_id"],
        "mission_run_id": provider_context["mission_run_id"],
        "business_id": provider_context["business_id"],
        "provider": provider_context["provider"],
        "tool_name": provider_context["tool_name"],
        "context_hash": provider_context["context_hash"],
        "credential_scope": provider_context["credential_scope"],
        "vault_reference_visible": False,
        "secret_material_exposed": contains_unredacted_secret_value(safe_page_state),
        "page_state": safe_page_state,
        "model_visible_context_hash": "",
    }

    if result["secret_material_exposed"]:
        raise ValueError("Model-visible context still contains unredacted secret values")

    result["model_visible_context_hash"] = _hash(
        {k: v for k, v in result.items() if k != "model_visible_context_hash"}
    )
    return result


def assert_context_mount_allowed(
    *,
    provider_context: dict[str, Any],
    mission_id: str,
    mission_run_id: str,
    provider: str,
    requested_action: str,
) -> dict[str, Any]:
    reasons: list[str] = []

    if provider_context["mission_id"] != mission_id:
        reasons.append("mission_context_mismatch")
    if provider_context["mission_run_id"] != mission_run_id:
        reasons.append("mission_run_context_mismatch")
    if provider_context["provider"] != provider:
        reasons.append("provider_context_mismatch")
    if requested_action not in provider_context["allowed_actions"]:
        reasons.append("action_outside_context_scope")
    if provider_context.get("secret_material_exposed") is True:
        reasons.append("secret_material_exposed")

    allowed = not reasons

    result = {
        "schema_version": "aion.provider_context_mount_assertion.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "provider": provider,
        "requested_action": requested_action,
        "context_hash": provider_context["context_hash"],
        "runtime_mount_allowed": allowed,
        "gateway_state": "context_mounted" if allowed else "context_mount_blocked",
        "reasons": reasons,
        "mount_assertion_hash": "",
    }
    result["mount_assertion_hash"] = _hash(
        {k: v for k, v in result.items() if k != "mount_assertion_hash"}
    )
    return result


def create_provider_context_receipt(
    *,
    mount_assertion: dict[str, Any],
) -> dict[str, Any]:
    if not mount_assertion["runtime_mount_allowed"]:
        raise ValueError("Cannot create provider context receipt for blocked mount")

    result = {
        "schema_version": "aion.provider_context_receipt.v0",
        "mission_id": mount_assertion["mission_id"],
        "mission_run_id": mount_assertion["mission_run_id"],
        "provider": mount_assertion["provider"],
        "requested_action": mount_assertion["requested_action"],
        "context_hash": mount_assertion["context_hash"],
        "mount_assertion_hash": mount_assertion["mount_assertion_hash"],
        "secret_material_exposed": False,
        "receipt_hash": "",
    }
    result["receipt_hash"] = _hash({k: v for k, v in result.items() if k != "receipt_hash"})
    return result
