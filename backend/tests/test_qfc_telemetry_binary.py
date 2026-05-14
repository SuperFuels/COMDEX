# backend/tests/test_qfc_telemetry_binary.py

import os
import json
import asyncio
import glob
import pytest

from backend.modules.photonlang.interpreter import run_source
from backend.modules.photonlang.interpreter import QuantumFieldCanvas, AtomSheet

# Create temp telemetry dir in test sandbox
TELEMETRY_DIR = "artifacts/telemetry"


@pytest.mark.asyncio
async def test_qfc_resonate_telemetry_and_binary(tmp_path, monkeypatch):
    # Patch telemetry output dir to temp location
    monkeypatch.setattr(
        "backend.modules.photonlang.integrations.photon_telemetry_recorder.RECORDER.base_dir",
        tmp_path
    )

    qfc = QuantumFieldCanvas()
    sheet = AtomSheet("test_sheet")
    qfc.inject(sheet)

    seq = "⊕⧖∇"

    # Run resonance
    result = await qfc.resonate(seq)

    # ✅ core resonance returned
    assert result["seq"] == seq
    assert isinstance(result["ops"], list)

    # ✅ binary output present
    assert "binary" in qfc.state
    assert qfc.state["binary"] != ""

    # ✅ SQI computed
    assert "sqi" in qfc.state
    assert isinstance(qfc.state["sqi"], float)

    # ✅ Telemetry file created
    files = list(tmp_path.glob("*.ptn"))
    assert len(files) == 1, "No telemetry file written"

    # ✅ Telemetry structure valid
    with open(files[0], "r") as f:
        data = json.load(f)

    assert "timestamp" in data
    assert "state" in data
    assert data["state"]["resonance"]["seq"] == seq
    assert "sqi_feedback" in data
    assert "qqc_feedback" in data


def test_interpreter_binary_output():
    result = run_source("⊕∇")

    assert result["binary"] != ""
    assert result["glyph_boot"] is True
    assert result["status"] == "success"