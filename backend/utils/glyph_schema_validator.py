# File: backend/utils/glyph_schema_validator.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Tuple

import jsonschema
from jsonschema import Draft7Validator, RefResolver, exceptions as jse

# Base folder: backend/schemas
SCHEMA_BASE = (Path(__file__).parent.parent / "schemas").resolve()
ATOM_SHEET_SCHEMA_PATH = SCHEMA_BASE / "atom_sheet.schema.json"
GLYPH_CELL_SCHEMA_PATH = SCHEMA_BASE / "glyph_cell_schema.json"

# Load schemas once at import (fail softly; raise later with clear message)
try:
    with open(ATOM_SHEET_SCHEMA_PATH, "r", encoding="utf-8") as f:
        _ATOM_SHEET_SCHEMA = json.load(f)
    with open(GLYPH_CELL_SCHEMA_PATH, "r", encoding="utf-8") as f:
        _GLYPH_CELL_SCHEMA = json.load(f)
    _SCHEMA_LOAD_ERR: Exception | None = None
except Exception as e:  # pragma: no cover - surfaced via _ensure_loaded()
    _ATOM_SHEET_SCHEMA = None
    _GLYPH_CELL_SCHEMA = None
    _SCHEMA_LOAD_ERR = e


def _ensure_loaded() -> None:
    if _SCHEMA_LOAD_ERR:
        raise RuntimeError(
            f"Schema load failed: {ATOM_SHEET_SCHEMA_PATH} / {GLYPH_CELL_SCHEMA_PATH} -> {_SCHEMA_LOAD_ERR}"
        )


def validate_glyph_cell(cell: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate a single GlyphCell against glyph_cell_schema.json
    """
    _ensure_loaded()
    try:
        Draft7Validator(_GLYPH_CELL_SCHEMA).validate(cell)
        return True, "Validation successful"
    except jse.ValidationError as ve:
        path = ".".join([str(p) for p in ve.path]) or "<root>"
        return False, f"GlyphCell invalid at {path}: {ve.message}"


def validate_atomsheet(sheet: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate an AtomSheet against atom_sheet.schema.json.
    NOTE: atom_sheet.schema.json should `$ref: "glyph_cell_schema.json"` for cells.items.
    """
    _ensure_loaded()
    try:
        # Resolve relative $ref ("glyph_cell_schema.json") from SCHEMA_BASE
        resolver = RefResolver(base_uri=SCHEMA_BASE.as_uri() + "/", referrer=_ATOM_SHEET_SCHEMA)
        Draft7Validator(_ATOM_SHEET_SCHEMA, resolver=resolver).validate(sheet)
        return True, "Sheet validation successful"
    except jse.ValidationError as ve:
        path = ".".join([str(p) for p in ve.path]) or "<root>"
        return False, f"AtomSheet invalid at {path}: {ve.message}"