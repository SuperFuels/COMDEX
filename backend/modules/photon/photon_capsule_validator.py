# backend/modules/photon/photon_capsule_validator.py

"""
🔷 Photon Capsule Validator - Schema Enforcement Layer (SRK-10)
Ensures all photon capsules conform to the canonical
`photon_capsule_schema.json` definition before QKD or Codex transfer.

Integrates seamlessly with:
 - photon_executor.py (runtime emission)
 - photon_to_codex.py (symbolic export)
 - qwave bridge layers (binary ↔ photon)

Implementation note:
This module intentionally delegates schema loading and validation to the
canonical utilities in `backend.modules.photon.validation` to avoid
duplication and path drift between photon/ and photonlang/. The public
API remains compatible and also re-exports the loaded schema for callers
that previously imported it from here.
"""

from __future__ import annotations

from typing import Any, Dict

# Canonical single-source validator + schema loader
from .validation import (
    validate_photon_capsule as _validate_photon_capsule,
    load_photon_capsule_schema,
)

# Optional: expose the schema for legacy callers that import from this module
CAPSULE_SCHEMA: Dict[str, Any] = load_photon_capsule_schema()

__all__ = [
    "assert_valid_capsule",
    "validate_photon_capsule",
    "CAPSULE_SCHEMA",
]

def validate_photon_capsule(capsule: Dict[str, Any]) -> None:
    """
    Validate a Photon Capsule instance against the canonical JSON schema.

    Raises jsonschema.ValidationError on failure.
    """
    _validate_photon_capsule(capsule)

def assert_valid_capsule(capsule: Dict[str, Any]) -> None:
    """
    Alias for validate_photon_capsule(); kept for callers that used
    assert_* semantics.
    """
    _validate_photon_capsule(capsule)