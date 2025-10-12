# backend/symatics/tests/test_visual_feedback.py
# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v1.2 — Visualization Feedback Tests
# Verifies CodexRender telemetry ingestion and visualization logic
# Author: Tessaris Core Systems / Codex Intelligence Group
# Version: v1.2.0 — October 2025
# ──────────────────────────────────────────────────────────────

import time
import numpy as np
import pytest

from backend.modules.codex import codex_render


@pytest.fixture(autouse=True)
def reset_buffer():
    """Ensure clean telemetry buffer before each test."""
    codex_render.telemetry_buffer.events.clear()
    codex_render.telemetry_buffer.events.extend([])
    yield
    codex_render.telemetry_buffer.events.clear()


# ──────────────────────────────────────────────────────────────
# 1️⃣ Basic Telemetry Recording
# ──────────────────────────────────────────────────────────────
def test_record_event_stores_payload():
    codex_render.record_event("law_weight_update", new_weight=1.23)
    events = codex_render.telemetry_buffer.snapshot()
    assert len(events) == 1
    ev = events[0]
    assert ev["event_type"] == "law_weight_update"
    assert pytest.approx(ev["new_weight"], rel=1e-6) == 1.23
    assert "timestamp" in ev


# ──────────────────────────────────────────────────────────────
# 2️⃣ CodexRender Ingestion and History
# ──────────────────────────────────────────────────────────────
def test_ingest_and_history_aggregation():
    # Simulate multiple telemetry streams
    codex_render.record_event("law_weight_update", new_weight=1.0)
    codex_render.record_event("wave_energy", value=0.9)
    codex_render.record_event("coherence_index", value=0.95)

    renderer = codex_render.CodexRender()
    renderer.ingest()

    # Validate all categories present
    hist = renderer.history
    assert "lambda" in hist
    assert "energy" in hist
    assert "coherence" in hist

    # Check stored values
    assert pytest.approx(hist["lambda"][0][1], rel=1e-6) == 1.0
    assert pytest.approx(hist["energy"][0][1], rel=1e-6) == 0.9
    assert pytest.approx(hist["coherence"][0][1], rel=1e-6) == 0.95


# ──────────────────────────────────────────────────────────────
# 3️⃣ Export Schema Verification
# ──────────────────────────────────────────────────────────────
def test_export_json_schema():
    codex_render.record_event("wave_energy", value=1.5)
    renderer = codex_render.CodexRender()
    renderer.ingest()
    data = renderer.export_json()

    assert isinstance(data, dict)
    assert "energy" in data
    entry = data["energy"][0]
    assert set(entry.keys()) == {"t", "v"}
    assert isinstance(entry["t"], float)
    assert isinstance(entry["v"], float)


# ──────────────────────────────────────────────────────────────
# 4️⃣ Plot Routine Smoke Test (headless)
# ──────────────────────────────────────────────────────────────
def test_plot_executes_without_error(monkeypatch):
    codex_render.record_event("law_weight_update", new_weight=1.0)
    codex_render.record_event("wave_energy", value=0.8)
    codex_render.record_event("coherence_index", value=0.9)

    renderer = codex_render.CodexRender()
    renderer.ingest()

    # Monkeypatch plt.show to avoid opening a window
    import matplotlib.pyplot as plt
    monkeypatch.setattr(plt, "show", lambda: None)

    # Should run cleanly
    renderer.plot()


# ──────────────────────────────────────────────────────────────
# 5️⃣ Continuous Update Scenario
# ──────────────────────────────────────────────────────────────
def test_continuous_telemetry_stream():
    for i in range(10):
        codex_render.record_event("law_weight_update", new_weight=1.0 + 0.01 * np.sin(i))
        codex_render.record_event("wave_energy", value=1.0 - 0.02 * i)
        codex_render.record_event("coherence_index", value=np.exp(-0.05 * i))
        time.sleep(0.001)

    renderer = codex_render.CodexRender()
    renderer.ingest()

    assert len(renderer.history["lambda"]) == 10
    assert len(renderer.history["energy"]) == 10
    assert len(renderer.history["coherence"]) == 10