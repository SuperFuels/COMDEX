import pytest

from backend.modules.atomsheets.atomsheet_engine import (
    load_sqs,
    execute_sheet,
    to_dc_json,
)

@pytest.mark.asyncio
async def test_atomsheet_load_execute_and_export():
    # --- Arrange: minimal .sqs.json in-memory ---
    sqs = {
        "id": "sheet_atoms_test",
        "title": "AtomSheet Exec Smoke",
        "dims": [1, 1, 1, 1],
        "cells": [
            {"id": "c1", "logic": "⊕ ∇ ↔ ⟲ → ✦", "position": [0, 0, 0, 0], "emotion": "neutral"},
            {"id": "c2", "logic": "⊕ ↔", "position": [0, 0, 0, 1]},
        ],
        "meta": {"owner": "tests"},
    }
    sheet = load_sqs(sqs)

    # --- Act: execute via QPU stack (silent: no WS broadcasts) ---
    ctx = {
        "benchmark_silent": True,
        "batch_collapse": True,  # sheet-level collapse beam for timeline
        # optional toggles:
        "phase9_enabled": False,
        "phase10_enabled": False,
    }
    results = await execute_sheet(sheet, ctx)

    # --- Assert: basic execution shape ---
    assert set(results.keys()) == {"c1", "c2"}
    assert isinstance(results["c1"], list)
    assert isinstance(results["c2"], list)

    # Each cell should have wave_beams and include the sheet-level collapse beam we appended
    for cid in ("c1", "c2"):
        cell = sheet.cells[cid]
        beams = getattr(cell, "wave_beams", [])
        assert isinstance(beams, list)
        assert any(b.get("source") == "atomsheet_execute" and b.get("stage") == "collapse" for b in beams)

    # --- Export shape check ---
    snap = to_dc_json(sheet)
    assert snap["id"] == "sheet_atoms_test"
    assert snap["type"] == "atomsheet_snapshot"
    assert "timestamp" in snap
    assert len(snap["cells"]) == 2
    # exported cells should carry wave_beams for replay
    for c in snap["cells"]:
        assert "wave_beams" in c
        assert isinstance(c["wave_beams"], list)