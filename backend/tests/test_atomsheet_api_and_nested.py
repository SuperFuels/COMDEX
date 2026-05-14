import json
import os
import pytest
from fastapi.testclient import TestClient

from backend.main import app  # your FastAPI app entry
from backend.modules.atomsheets.atomsheet_engine import load_atom, execute_sheet

client = TestClient(app)

@pytest.mark.asyncio
async def test_atomsheet_api_and_nested(tmp_path):
    # parent with nested inline child
    child = {
        "id": "child_sheet",
        "title": "Child",
        "dims": [1,1,1,1],
        "cells": [
            {"id": "k1", "logic": "⊕ ↔", "position":[0,0,0,0]}
        ]
    }
    parent = {
        "id": "parent_sheet",
        "title": "Parent",
        "dims": [1,1,1,1],
        "cells": [
            {
                "id": "p1",
                "logic": "∇",
                "position": [0,0,0,0],
                "meta": {"nested": {"type": "inline", "sheet": child}}
            }
        ]
    }
    # write .atom
    atom_path = tmp_path / "demo.atom"
    with open(atom_path, "w") as f:
        json.dump(parent, f)

    # GET load
    r = client.get(f"/api/atomsheet?file={atom_path}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "parent_sheet"
    assert len(data["cells"]) == 1

    # POST execute with nested expansion
    payload = {
        "file": str(atom_path),
        "container_id": "demo_container",
        "options": {"benchmark_silent": True, "batch_collapse": True, "expand_nested": True}
    }
    r2 = client.post("/api/atomsheet/execute", json=payload)
    assert r2.status_code == 200
    out = r2.json()
    assert out["ok"] is True
    assert out["sheet_id"] == "parent_sheet"
    assert "p1" in out["beam_counts"]

    # Direct engine check for the expand beam
    sheet = load_atom(str(atom_path))
    res = await execute_sheet(sheet, {"benchmark_silent": True, "expand_nested": True})
    beams = sheet.cells["p1"].wave_beams
    assert any(b.get("stage") == "expand" and b.get("source") == "atomsheet_nested" for b in beams)