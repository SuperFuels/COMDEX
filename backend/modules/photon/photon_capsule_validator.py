import json
import jsonschema
from pathlib import Path
from typing import Dict, Any

SCHEMA_PATH = Path(__file__).with_name("photon_capsule_schema.json")

with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    CAPSULE_SCHEMA = json.load(f)

def validate_photon_capsule(capsule: Dict[str, Any]) -> None:
    """
    Validate a Photon capsule against the schema.
    Raises jsonschema.ValidationError if invalid.
    """
    jsonschema.validate(instance=capsule, schema=CAPSULE_SCHEMA)