# File: tools/lint_atomsheet.py
# 🔍 CLI tool to lint .sqs.json AtomSheets against atomsheet_schema.json + glyph_cell_schema.json

import json
import sys
import os
from pathlib import Path
from jsonschema import validate, ValidationError, RefResolver

# Configurable paths via environment variable
ATOM_SHEET_SCHEMA_PATH = Path(os.getenv("ATOM_SHEET_SCHEMA_PATH", "backend/schemas/atomsheet_schema.json"))
GLYPH_CELL_SCHEMA_PATH = Path(os.getenv("GLYPH_CELL_SCHEMA_PATH", "backend/schemas/glyph_cell_schema.json"))

# Load schemas once
atomsheet_schema = None
glyph_schema = None

def get_atomsheet_schema():
    global atomsheet_schema
    if atomsheet_schema is None:
        try:
            with open(ATOM_SHEET_SCHEMA_PATH, "r") as f:
                atomsheet_schema = json.load(f)
        except FileNotFoundError:
            print(f"❌ AtomSheet schema not found at {ATOM_SHEET_SCHEMA_PATH}")
            sys.exit(1)
    return atomsheet_schema

def get_glyph_schema():
    global glyph_schema
    if glyph_schema is None:
        try:
            with open(GLYPH_CELL_SCHEMA_PATH, "r") as f:
                glyph_schema = json.load(f)
        except FileNotFoundError:
            print(f"❌ GlyphCell schema not found at {GLYPH_CELL_SCHEMA_PATH}")
            sys.exit(1)
    return glyph_schema

def validate_glyph_cell(cell: dict, index: int = 0) -> bool:
    try:
        validate(instance=cell, schema=get_glyph_schema())
        return True
    except ValidationError as ve:
        print(f"❌ Cell {cell.get('id') or f'#{index}'} failed schema validation:")
        print(f"   ↳ {ve.message}")
        return False

def lint_atomsheet(filepath: Path, json_output: bool = False):
    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        return

    try:
        with open(filepath, "r") as f:
            data = json.load(f)

        # Use schema with resolver to support $ref to glyph schema
        resolver = RefResolver(base_uri=str(GLYPH_CELL_SCHEMA_PATH.resolve().as_uri()), referrer=get_atomsheet_schema())
        validate(instance=data, schema=get_atomsheet_schema(), resolver=resolver)

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return
    except ValidationError as ve:
        print(f"❌ Top-level validation failed: {ve.message}")
        return

    cells = data.get("cells", [])
    print(f"🔍 Linting file: {filepath}")
    print(f"📦 Total cells: {len(cells)}\n")

    valid_count = 0
    errors = []

    for i, cell in enumerate(cells):
        if validate_glyph_cell(cell, i):
            print(f"✅ Cell {cell.get('id') or f'#{i}'} is valid")
            valid_count += 1
        else:
            errors.append(cell.get('id') or f"#{i}")

    print(f"\n✅ {valid_count}/{len(cells)} cells passed schema validation.")

    if json_output:
        return {
            "file": str(filepath),
            "valid_cells": valid_count,
            "total_cells": len(cells),
            "errors": errors
        }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/lint_atomsheet.py path/to/example_sheet.sqs.json [--json]")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    json_flag = "--json" in sys.argv
    result = lint_atomsheet(file_path, json_output=json_flag)

    if json_flag and result:
        print(json.dumps(result, indent=2))