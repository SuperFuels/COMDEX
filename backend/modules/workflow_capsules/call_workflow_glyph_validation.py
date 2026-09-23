from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


JsonDict = dict[str, Any]


@dataclass(frozen=True)
class CallWorkflowGlyphValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_connectors: list[str] = field(default_factory=list)
    version_mismatch: bool = False
    approval_policy_mismatch: bool = False
    runtime_blocked: bool = False

    def to_dict(self) -> JsonDict:
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "missing_connectors": list(self.missing_connectors),
            "version_mismatch": self.version_mismatch,
            "approval_policy_mismatch": self.approval_policy_mismatch,
            "runtime_blocked": self.runtime_blocked,
        }


def _as_dict(value: Any) -> JsonDict:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _schema_properties(schema: Any) -> JsonDict:
    schema = _as_dict(schema)
    props = schema.get("properties")
    return props if isinstance(props, dict) else {}


def _schema_required(schema: Any) -> list[str]:
    schema = _as_dict(schema)
    return [str(x) for x in _as_list(schema.get("required")) if str(x).strip()]


def _schema_type(schema_or_property: Any) -> str | None:
    value = _as_dict(schema_or_property).get("type")
    return str(value) if value else None


def _payload_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _type_matches(expected: str | None, actual: str | None) -> bool:
    if not expected or not actual:
        return True
    if expected == actual:
        return True
    if expected == "number" and actual == "integer":
        return True
    return False


def _normalise_connector_ids(items: Any) -> set[str]:
    out: set[str] = set()

    if isinstance(items, dict):
        for key, value in items.items():
            if value is True:
                out.add(str(key).lower())
            elif isinstance(value, dict) and (
                value.get("connected") is True
                or value.get("available") is True
                or value.get("ok") is True
            ):
                out.add(str(key).lower())
        return out

    for item in _as_list(items):
        if isinstance(item, str):
            out.add(item.lower())
        elif isinstance(item, dict):
            for key in ("id", "key", "name", "connector", "provider"):
                if item.get(key):
                    out.add(str(item[key]).lower())

    return out


def _approval_requires_approval(policy: Any) -> bool:
    policy = _as_dict(policy)
    return bool(
        policy.get("approval_before_external_write") is True
        or policy.get("requires_approval") is True
        or policy.get("human_approval_required") is True
        or str(policy.get("mode", "")).lower() in {"approval_required", "review", "manual_review"}
    )


def validate_call_workflow_glyph_contract(
    *,
    parent_output_schema: Any | None = None,
    parent_output_payload: Any | None = None,
    child_output_payload: Any | None = None,
    call_node: Any,
    registry_glyph: Any | None = None,
    available_connectors: Any | None = None,
    parent_approval_policy: Any | None = None,
) -> CallWorkflowGlyphValidationResult:
    """
    Pure validation for staged call_workflow_glyph nodes.

    It does not execute workflows.
    It does not mutate graph state.
    It does not call AI.
    It does not write to backend storage.
    """
    node = _as_dict(call_node)
    config = _as_dict(node.get("config"))
    registry = _as_dict(registry_glyph)

    errors: list[str] = []
    warnings: list[str] = []

    glyph_code = node.get("glyph_code") or config.get("glyph_code") or registry.get("glyph_code")
    if not glyph_code:
        errors.append("missing_glyph_code")

    child_workflow_id = (
        node.get("child_workflow_id")
        or config.get("child_workflow_id")
        or registry.get("workflow_id")
        or registry.get("child_workflow_id")
    )
    if not child_workflow_id:
        errors.append("missing_child_workflow_id")

    child_input_schema = (
        node.get("input_schema")
        or config.get("input_schema")
        or config.get("inputs_schema")
        or registry.get("input_schema")
        or registry.get("inputs_schema")
        or {}
    )

    child_output_schema = (
        node.get("output_schema")
        or config.get("output_schema")
        or config.get("outputs_schema")
        or registry.get("output_schema")
        or registry.get("outputs_schema")
        or {}
    )

    required_connectors = (
        node.get("required_connectors")
        or config.get("required_connectors")
        or registry.get("required_connectors")
        or []
    )

    node_version = node.get("glyph_version") or config.get("glyph_version") or "v1"
    registry_version = registry.get("glyph_version") or registry.get("workflow_version") or registry.get("version")

    node_hash = node.get("version_hash") or config.get("version_hash")
    registry_hash = registry.get("version_hash") or _as_dict(registry.get("meta")).get("version_hash")

    version_mismatch = False
    if registry:
        if registry_version and str(node_version) != str(registry_version):
            version_mismatch = True
            errors.append("pinned_glyph_version_mismatch")
        if node_hash and registry_hash and str(node_hash) != str(registry_hash):
            version_mismatch = True
            errors.append("pinned_glyph_hash_mismatch")

    # Connector validation contract:
    # - available_connectors=None means connector registry is unknown, so avoid a false hard error.
    # - available_connectors=[] means registry is known and empty, so required connectors are missing.
    # - available_connectors=[...] validates normally.
    available = _normalise_connector_ids(available_connectors)
    required = [str(x) for x in _as_list(required_connectors) if str(x).strip()]

    if available_connectors is None:
        missing_connectors = []
    else:
        missing_connectors = [x for x in required if x.lower() not in available]

    if missing_connectors:
        errors.append("missing_required_connectors")

    parent_props = _schema_properties(parent_output_schema)
    child_input_props = _schema_properties(child_input_schema)
    child_required = _schema_required(child_input_schema)

    payload = parent_output_payload if isinstance(parent_output_payload, dict) else None

    for key in child_required:
        if payload is not None:
            if key not in payload:
                errors.append(f"parent_output_missing_child_input:{key}")
        elif key not in parent_props:
            errors.append(f"parent_output_schema_missing_child_input:{key}")

    for key, child_prop_schema in child_input_props.items():
        parent_prop_schema = parent_props.get(key)
        if parent_prop_schema:
            parent_type = _schema_type(parent_prop_schema)
            child_type = _schema_type(child_prop_schema)
            if not _type_matches(child_type, parent_type):
                errors.append(f"parent_child_input_type_mismatch:{key}:{parent_type}->{child_type}")

        if payload is not None and key in payload:
            expected = _schema_type(child_prop_schema)
            actual = _payload_type(payload[key])
            if not _type_matches(expected, actual):
                errors.append(f"parent_payload_child_input_type_mismatch:{key}:{actual}->{expected}")

    if child_output_schema and _schema_type(child_output_schema) not in {None, "object"}:
        errors.append("child_output_schema_must_be_object")

    if isinstance(child_output_payload, dict):
        child_output_props = _schema_properties(child_output_schema)
        for key, prop_schema in child_output_props.items():
            if key in child_output_payload:
                expected = _schema_type(prop_schema)
                actual = _payload_type(child_output_payload[key])
                if not _type_matches(expected, actual):
                    errors.append(f"child_output_type_mismatch:{key}:{actual}->{expected}")

    node_policy = (
        node.get("approval_policy")
        or config.get("approval_policy")
        or registry.get("approval_policy")
        or {}
    )

    approval_policy_mismatch = False
    if _approval_requires_approval(node_policy) and not _approval_requires_approval(parent_approval_policy):
        approval_policy_mismatch = True
        errors.append("approval_policy_mismatch")

    dry_run_only = (
        node.get("dry_run_only") is not False
        and config.get("dry_run_only") is not False
        and _as_dict(node.get("runtime_plan") or config.get("runtime_plan") or registry.get("runtime_plan")).get("dry_run_only") is not False
    )
    live_send_enabled = (
        node.get("live_send_enabled") is True
        or config.get("live_send_enabled") is True
        or _as_dict(node.get("runtime_plan") or config.get("runtime_plan") or registry.get("runtime_plan")).get("live_send_enabled") is True
    )

    if live_send_enabled and dry_run_only:
        warnings.append("live_send_enabled_ignored_in_dry_run")

    if live_send_enabled and not _approval_requires_approval(node_policy):
        errors.append("live_send_requires_approval_policy")

    valid = not errors
    runtime_blocked = not valid

    return CallWorkflowGlyphValidationResult(
        valid=valid,
        errors=errors,
        warnings=warnings,
        missing_connectors=missing_connectors,
        version_mismatch=version_mismatch,
        approval_policy_mismatch=approval_policy_mismatch,
        runtime_blocked=runtime_blocked,
    )
