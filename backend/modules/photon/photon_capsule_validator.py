"""
🔷 Photon Capsule Validator — Schema Enforcement Layer (SRK-10)
Ensures all photon capsules conform to the canonical
`photon_capsule_schema.json` definition before QKD or Codex transfer.

Integrates seamlessly with:
 - photon_executor.py (runtime emission)
 - photon_to_codex.py (symbolic export)
 - qwave bridge layers (binary ↔ photon)
"""

import json
import jsonschema
from pathlib import Path
from typing import Dict, Any


# ────────────────────────────────────────────────────────────────
# 📘 Load canonical Photon Capsule schema
# ----------------------------------------------------------------
SCHEMA_PATH = Path(__file__).with_name("photon_capsule_schema.json")

try:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        CAPSULE_SCHEMA = json.load(f)
except FileNotFoundError as e:
    raise FileNotFoundError(f"Photon capsule schema not found at: {SCHEMA_PATH}") from e


# ────────────────────────────────────────────────────────────────
# ✅ Validation Function
# ----------------------------------------------------------------
def validate_photon_capsule(capsule: Dict[str, Any]) -> None:
    """
    Validate a Photon Capsule instance against its JSON schema.

    Args:
        capsule (Dict[str, Any]): Photon capsule to validate.

    Raises:
        jsonschema.ValidationError: if capsule violates schema.
        FileNotFoundError: if schema file missing.
    """
    try:
        jsonschema.validate(instance=capsule, schema=CAPSULE_SCHEMA)
    except jsonschema.ValidationError as e:
        raise jsonschema.ValidationError(
            f"[Photon Capsule Validation Error] {e.message} at path: "
            f"{'/'.join(map(str, e.path))}"
        ) from e