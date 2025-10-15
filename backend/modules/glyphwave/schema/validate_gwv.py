"""
🧩 GWV Schema Validator — SRK-19 Task 4
Validates Graphical Wave Visualization (.gwv) files against the official
schema definition (v1.1). Ensures data integrity before analysis or replay.
"""

import json
import os
from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource


SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__),
    "gwv_schema_v1_1.json"
)


def _load_schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_gwv_file(path: str) -> bool:
    """
    Validate a .gwv file against the official GWV Schema v1.1.
    Raises jsonschema.ValidationError on failure.

    Returns True if validation passes.
    """
    schema = _load_schema()

    # ✅ Modern referencing-based registry (replaces RefResolver)
    registry = Registry().with_resource(
        f"file://{SCHEMA_PATH}",
        Resource.from_contents(schema)
    )
    validator = Draft202012Validator(schema, registry=registry)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    validator.validate(data)
    return True


def safe_validate_gwv(path: str) -> bool:
    """
    Wrapper for validation that returns False instead of raising.
    """
    try:
        return validate_gwv_file(path)
    except ValidationError as e:
        print(f"[GWVValidator] Validation failed for {path}: {e.message}")
        return False
    except Exception as e:
        print(f"[GWVValidator] Unexpected error validating {path}: {e}")
        return False