from __future__ import annotations

from typing import Any, Optional
import logging

from .schema_registry import REGISTRY

log = logging.getLogger("aion_equities.schema_validate")

try:
    import jsonschema
    from jsonschema import Draft202012Validator
except Exception:  # pragma: no cover - graceful fallback if dependency missing
    jsonschema = None
    Draft202012Validator = None


class SchemaValidationError(ValueError):
    """Raised when a payload fails schema validation."""


def _format_jsonschema_error(err: Any) -> str:
    # err.path is a deque-like path into the payload
    try:
        path = list(err.path)
    except Exception:
        path = []
    dotted = ".".join(str(p) for p in path) if path else "<root>"
    return f"{dotted}: {err.message}"


def validate_payload(
    schema_name: str,
    payload: dict,
    *,
    version: Optional[str] = None,
    require_jsonschema: bool = True,
) -> None:
    """
    Validate a payload against a named AION equities schema.

    Raises:
      - SchemaValidationError on validation failure
      - RuntimeError if jsonschema package is unavailable (unless require_jsonschema=False)
    """
    if not isinstance(payload, dict):
        raise SchemaValidationError(f"Payload for {schema_name} must be a dict, got {type(payload).__name__}")

    schema = REGISTRY.load_json(schema_name, version=version)

    if Draft202012Validator is None:
        msg = "jsonschema is not installed; cannot validate schema payloads."
        if require_jsonschema:
            raise RuntimeError(msg)
        log.warning(msg)
        return

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
    if errors:
        details = "; ".join(_format_jsonschema_error(e) for e in errors[:8])
        # cap output to avoid huge logs
        raise SchemaValidationError(f"{schema_name} validation failed: {details}")

    log.debug("Validated payload for schema=%s version=%s", schema_name, version or REGISTRY.default_version)


def validate_or_false(schema_name: str, payload: dict, *, version: Optional[str] = None) -> bool:
    """Boolean helper for non-throwing validation checks."""
    try:
        validate_payload(schema_name, payload, version=version)
        return True
    except Exception as e:
        log.warning("Validation failed for schema=%s: %s", schema_name, e)
        return False