# backend/modules/photon/validation.py
from __future__ import annotations

from typing import Any, Dict
from jsonschema import Draft7Validator
from .schema import load_photon_capsule_schema as _load_schema

# Load once and cache
_SCHEMA: Dict[str, Any] = _load_schema()
_VALIDATOR = Draft7Validator(_SCHEMA)

def load_photon_capsule_schema() -> Dict[str, Any]:
    """Return the parsed JSON schema dict (back-compat export)."""
    return _SCHEMA

def validate_photon_capsule(capsule: Dict[str, Any]) -> None:
    """
    Validate an object against the Photon capsule schema.
    Raises jsonschema.ValidationError on failure.
    """
    _VALIDATOR.validate(capsule)