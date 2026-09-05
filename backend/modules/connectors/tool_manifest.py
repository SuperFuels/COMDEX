from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List


SCHEMA_VERSION = "aion.third_party_tool.v1"
VALID_CONNECTION_TYPES = {
    "oauth2",
    "api_key",
    "webhook",
    "mcp",
    "local_service",
    "browser_session",
    "desktop_control",
}
VALID_ACTION_KINDS = {"trigger", "read", "draft", "write", "delete", "financial", "custom_api"}
VALID_RISK_TIERS = {"low", "medium", "high", "blocked"}
VALID_AUTHORITY_MODES = {"ask_each_time", "auto_within_limits", "full_access", "blocked"}
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")
_SECRET_KEYS = {"api_key", "access_token", "refresh_token", "password", "client_secret", "private_key"}


class ToolManifestError(ValueError):
    """Raised when a third-party tool manifest violates AION's integration contract."""


def _required(mapping: Dict[str, Any], keys: Iterable[str], path: str, errors: List[str]) -> None:
    for key in keys:
        if key not in mapping or mapping[key] in (None, "", []):
            errors.append(f"{path}.{key}:required")


def _find_embedded_secrets(value: Any, path: str = "manifest") -> List[str]:
    errors: List[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).lower() in _SECRET_KEYS and child not in (None, "", "REDACTED"):
                errors.append(f"{child_path}:secret_must_live_in_vault")
            errors.extend(_find_embedded_secrets(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_find_embedded_secrets(child, f"{path}[{index}]"))
    return errors


def validate_tool_manifest(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and fingerprint a provider manifest.

    The manifest describes powers and controls; it never stores credentials.
    A valid manifest does not make an adapter live. Runtime registration,
    credential health, authority evaluation and a verified execution receipt
    remain separate gates.
    """

    errors: List[str] = []
    if not isinstance(manifest, dict):
        raise ToolManifestError("manifest:object_required")

    _required(manifest, ["schema_version", "tool", "connection", "skills", "actions", "governance"], "manifest", errors)
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"manifest.schema_version:expected_{SCHEMA_VERSION}")

    tool = manifest.get("tool")
    if isinstance(tool, dict):
        _required(tool, ["tool_id", "label", "category", "owner"], "manifest.tool", errors)
        tool_id = str(tool.get("tool_id") or "")
        if tool_id and not _IDENTIFIER.fullmatch(tool_id):
            errors.append("manifest.tool.tool_id:invalid_identifier")
    else:
        errors.append("manifest.tool:object_required")
        tool_id = ""

    connection = manifest.get("connection")
    if isinstance(connection, dict):
        _required(
            connection,
            ["type", "vault_reference", "least_privilege_scopes", "health_check", "revocation_method"],
            "manifest.connection",
            errors,
        )
        if connection.get("type") not in VALID_CONNECTION_TYPES:
            errors.append("manifest.connection.type:unsupported")
        vault_reference = str(connection.get("vault_reference") or "")
        if vault_reference and not vault_reference.startswith("vault."):
            errors.append("manifest.connection.vault_reference:must_reference_vault")
    else:
        errors.append("manifest.connection:object_required")

    skills = manifest.get("skills")
    skill_ids: set[str] = set()
    if isinstance(skills, list):
        for index, skill in enumerate(skills):
            path = f"manifest.skills[{index}]"
            if not isinstance(skill, dict):
                errors.append(f"{path}:object_required")
                continue
            _required(skill, ["skill_id", "description", "required_knowledge"], path, errors)
            skill_id = str(skill.get("skill_id") or "")
            if skill_id and not _IDENTIFIER.fullmatch(skill_id):
                errors.append(f"{path}.skill_id:invalid_identifier")
            if skill_id in skill_ids:
                errors.append(f"{path}.skill_id:duplicate")
            skill_ids.add(skill_id)
    else:
        errors.append("manifest.skills:list_required")

    actions = manifest.get("actions")
    action_ids: set[str] = set()
    if isinstance(actions, list):
        for index, action in enumerate(actions):
            path = f"manifest.actions[{index}]"
            if not isinstance(action, dict):
                errors.append(f"{path}:object_required")
                continue
            _required(
                action,
                ["action_id", "label", "description", "kind", "skill_ids", "input_contract", "output_contract", "risk", "authority", "execution", "receipt", "failure"],
                path,
                errors,
            )
            action_id = str(action.get("action_id") or "")
            if action_id and not _IDENTIFIER.fullmatch(action_id):
                errors.append(f"{path}.action_id:invalid_identifier")
            if tool_id and action_id and not action_id.startswith(f"{tool_id}."):
                errors.append(f"{path}.action_id:must_use_tool_prefix")
            if action_id in action_ids:
                errors.append(f"{path}.action_id:duplicate")
            action_ids.add(action_id)
            if action.get("kind") not in VALID_ACTION_KINDS:
                errors.append(f"{path}.kind:unsupported")

            for skill_id in action.get("skill_ids") or []:
                if skill_id not in skill_ids:
                    errors.append(f"{path}.skill_ids:unknown_{skill_id}")

            risk = action.get("risk") if isinstance(action.get("risk"), dict) else {}
            authority = action.get("authority") if isinstance(action.get("authority"), dict) else {}
            execution = action.get("execution") if isinstance(action.get("execution"), dict) else {}
            receipt = action.get("receipt") if isinstance(action.get("receipt"), dict) else {}
            failure = action.get("failure") if isinstance(action.get("failure"), dict) else {}
            _required(risk, ["tier", "external_write", "financial", "reversible", "data_classes"], f"{path}.risk", errors)
            _required(authority, ["policy_key", "default_mode", "allowed_modes", "constraints"], f"{path}.authority", errors)
            _required(execution, ["adapter_method", "dry_run_supported", "idempotency", "timeout_seconds"], f"{path}.execution", errors)
            _required(receipt, ["required", "success_fields", "reconciliation"], f"{path}.receipt", errors)
            _required(failure, ["fail_closed", "retryable_errors", "user_message"], f"{path}.failure", errors)

            if risk.get("tier") not in VALID_RISK_TIERS:
                errors.append(f"{path}.risk.tier:unsupported")
            if authority.get("default_mode") not in VALID_AUTHORITY_MODES:
                errors.append(f"{path}.authority.default_mode:unsupported")
            for mode in authority.get("allowed_modes") or []:
                if mode not in VALID_AUTHORITY_MODES:
                    errors.append(f"{path}.authority.allowed_modes:unsupported_{mode}")

            external_write = risk.get("external_write") is True
            financial = risk.get("financial") is True or action.get("kind") == "financial"
            if external_write:
                if receipt.get("required") is not True:
                    errors.append(f"{path}.receipt.required:external_write_requires_receipt")
                if failure.get("fail_closed") is not True:
                    errors.append(f"{path}.failure.fail_closed:external_write_must_fail_closed")
                if execution.get("idempotency") not in {"required", "provider_managed"}:
                    errors.append(f"{path}.execution.idempotency:external_write_requires_idempotency")
            if financial:
                constraints = authority.get("constraints") if isinstance(authority.get("constraints"), dict) else {}
                if constraints.get("amount_limit_required") is not True:
                    errors.append(f"{path}.authority.constraints:financial_limit_required")
                if not constraints.get("currency"):
                    errors.append(f"{path}.authority.constraints:financial_currency_required")
            if risk.get("tier") in {"high", "blocked"} and authority.get("default_mode") == "full_access":
                errors.append(f"{path}.authority.default_mode:high_risk_cannot_default_full_access")

    else:
        errors.append("manifest.actions:list_required")

    governance = manifest.get("governance")
    if isinstance(governance, dict):
        _required(
            governance,
            ["data_retention", "audit_log", "kill_switch", "promotion_evidence", "claim_boundary"],
            "manifest.governance",
            errors,
        )
    else:
        errors.append("manifest.governance:object_required")

    errors.extend(_find_embedded_secrets(manifest))
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    result = {
        "valid": not errors,
        "schema_version": SCHEMA_VERSION,
        "tool_id": tool_id or None,
        "action_count": len(actions) if isinstance(actions, list) else 0,
        "manifest_sha256": hashlib.sha256(canonical).hexdigest(),
        "errors": errors,
    }
    if errors:
        raise ToolManifestError(";".join(errors))
    return result


def load_and_validate_tool_manifest(path: str | Path) -> Dict[str, Any]:
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    return validate_tool_manifest(payload)

