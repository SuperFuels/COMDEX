# File: backend/tests/test_symbolic_spreadsheet_engine.py

import os
import pytest

from backend.modules.symbolic_spreadsheet.engine.symbolic_spreadsheet_engine import (
    load_sqs, execute_sheet
)
from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell

TEST_SHEET_PATH = "backend/data/sheets/example_sheet.sqs.json"


def test_load_sqs_file():
    """📥 Test loading the symbolic spreadsheet .sqs.json file."""
    assert os.path.exists(TEST_SHEET_PATH), f"❌ Missing file: {TEST_SHEET_PATH}"
    sheet = load_sqs(TEST_SHEET_PATH)
    assert isinstance(sheet, list), "❌ Sheet did not load as a list"
    assert all(isinstance(cell, GlyphCell) for cell in sheet), "❌ Not all entries are GlyphCells"
    assert len(sheet) > 0, "❌ No cells found in sheet"
    assert all(len(cell.position) == 4 for cell in sheet), "❌ Not all positions are 4D"
    print(f"✅ Loaded {len(sheet)} cells")


def test_execute_sheet_sqi_bounds():
    """⚙️ Execute the sheet and validate SQI scores are within bounds."""
    sheet = load_sqs(TEST_SHEET_PATH)
    execute_sheet(sheet)

    for cell in sheet:
        print(f"[Test] {cell}")
        assert isinstance(cell.result, str), f"❌ Missing execution result in {cell.id}"
        assert 0.0 <= cell.sqi_score <= 1.0, f"❌ SQI out of bounds: {cell.sqi_score} in {cell.id}"


def test_ethics_validation_blocks_illegal_cells():
    """
    🔒 Test that logic with disallowed terms (e.g., 'overwrite') is blocked by SoulLaw.
    """
    sheet = load_sqs(TEST_SHEET_PATH)
    execute_sheet(sheet)

    for cell in sheet:
        if "overwrite" in cell.logic.lower():
            assert not cell.validated, f"❌ Cell {cell.id} should have failed ethics validation"
            assert "Blocked by SoulLaw" in cell.result, f"❌ Ethics block not reported in {cell.id}"
        else:
            assert cell.validated, f"❌ Cell {cell.id} unexpectedly failed validation"


if __name__ == "__main__":
    # Optional: Run manually for debug/dev mode
    print("🔬 Running symbolic spreadsheet engine tests manually...")
    test_load_sqs_file()
    test_execute_sheet_sqi_bounds()
    test_ethics_validation_blocks_illegal_cells()
    print("✅ All tests completed.")