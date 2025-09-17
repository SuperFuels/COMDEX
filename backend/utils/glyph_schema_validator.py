# File: backend/utils/glyph_schema_validator.py

import json
import jsonschema
from jsonschema import validate
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "glyph_cell_schema.json"
with open(SCHEMA_PATH) as f:
    glyph_schema = json.load(f)

def validate_glyph_cell(cell: dict) -> tuple[bool, str]:
    try:
        validate(instance=cell, schema=glyph_schema["properties"]["cells"]["items"])
        return True, "Validation successful"
    except jsonschema.exceptions.ValidationError as ve:
        return False, f"GlyphCell validation error: {ve.message}"

def validate_atomsheet(sheet_dict: dict) -> tuple[bool, str]:
    try:
        validate(instance=sheet_dict, schema=glyph_schema)
        return True, "Sheet validation successful"
    except jsonschema.exceptions.ValidationError as ve:
        return False, f"AtomSheet validation error: {ve.message}"