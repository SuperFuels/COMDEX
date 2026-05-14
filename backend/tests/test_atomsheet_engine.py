# backend/tests/test_atomsheet_atom_loader.py
import json
import pytest

from backend.modules.atomsheets.atomsheet_engine import (
    load_sqs,        # alias -> load_atom
    execute_sheet,   # async
    to_dc_json,      # export helper
)

@pytest.mark.asyncio
async def test_atomsheet_load_execute_and_export_from_atom(tmp_path):
    # --- Arrange: write a real .atom file on disk ---
    test_data = {
        "id": "sheet_atoms_test",
        "title": "AtomSheet Exec Smoke",
        "dims": [1, 1, 1, 1],
        "cells": [
            {"id": "c1", "logic": "⊕ ∇ ↔ ⟲ -> ✦", "position": [0, 0, 0, 0], "emotion": "neutral"},
            {"id": "c2", "logic": "⊕ ↔",           "position": [0, 0, 0, 1]},
        ],
        "meta": {"owner": "tests"},
    }
    atom_path = tmp_path / "test.atom"
    with open(atom_path, "w") as f:
        json.dump(test_data, f)

    # --- Load (alias load_sqs -> load_atom still works) ---
    sheet = load_sqs(str(atom_path))

    # --- Act: execute via QPU stack (silent: no WS broadcasts) ---
    ctx = {
        "benchmark_silent": True,
        "batch_collapse": True,   # add sheet-level collapse beam
        # optional toggles (off here for a tight smoke):
        "phase9_enabled": False,
        "phase10_enabled": False,
    }
    results = await execute_sheet(sheet, ctx)

    # --- Assert: basic execution shape ---
    assert set(results.keys()) == {"c1", "c2"}
    assert isinstance(results["c1"], list)
    assert isinstance(results["c2"], list)

    # Each cell should have beams and include the sheet-level collapse beam
    for cid in ("c1", "c2"):
        cell = sheet.cells[cid]
        beams = getattr(cell, "wave_beams", [])
        assert isinstance(beams, list)
        assert any(
            b.get("source") == "atomsheet_execute" and b.get("stage") == "collapse"
            for b in beams
        )

    # --- Export to .dc.json and verify shape ---
    out_path = tmp_path / "test.dc.json"
    snap = to_dc_json(sheet, str(out_path))

    assert snap["id"] == "sheet_atoms_test"
    assert snap["type"] == "atomsheet_snapshot"
    assert "timestamp" in snap
    assert len(snap["cells"]) == 2

    # exported cells should carry wave_beams for replay
    for c in snap["cells"]:
        assert "wave_beams" in c
        assert isinstance(c["wave_beams"], list)