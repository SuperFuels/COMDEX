# ──────────────────────────────────────────────────────────────
# Tessaris Symatics v1.1 - Δ-Telemetry Integration Test Suite
# Validates real-time emission from AdaptiveLawEngine + WaveDiffEngine
# ──────────────────────────────────────────────────────────────

import numpy as np
import time
import types

import pytest

from backend.symatics.core.adaptive_laws import AdaptiveLawEngine
from backend.symatics.core.wave_diff_engine import WaveDiffEngine


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────
@pytest.fixture
def mock_record(monkeypatch):
    """Patch record_event to capture telemetry metrics."""
    events = []

    def _mock_record(event_type: str, **fields):
        events.append((event_type, fields))
        return True

    monkeypatch.setattr(
        "backend.symatics.core.adaptive_laws.record_event", _mock_record
    )
    monkeypatch.setattr(
        "backend.symatics.core.wave_diff_engine.record_event", _mock_record
    )
    return events


# ──────────────────────────────────────────────────────────────
# Adaptive Law Telemetry Tests
# ──────────────────────────────────────────────────────────────
def test_adaptive_law_emits_telemetry(mock_record):
    engine = AdaptiveLawEngine()
    for drift in [0.0, 0.05, 0.1]:
        engine.update("law_equivalence", drift)

    events = [ev for ev in mock_record if ev[0] == "law_weight_update"]
    assert events, "No law_weight_update events recorded"

    # Check last event metrics
    _, fields = events[-1]
    assert "lambda_rate" in fields
    assert "new_weight" in fields
    assert fields["telemetry_mode"] in ("CodexTrace", "SymaticsChannel", "None")


# ──────────────────────────────────────────────────────────────
# Wave Diff Telemetry Tests
# ──────────────────────────────────────────────────────────────
def test_wave_engine_emits_energy_and_coherence(mock_record):
    ψ = np.outer(np.linspace(0, 1, 4), np.linspace(0, 1, 4))
    λ = np.ones_like(ψ) * 0.5
    engine = WaveDiffEngine()
    engine.register_field("ψ", ψ)
    engine.register_field("λ", λ)

    engine.step("ψ", "λ", dt=0.2)
    events = [ev for ev in mock_record if ev[0] == "wave_step"]
    assert events, "No wave_step telemetry recorded"

    # Validate telemetry content
    _, fields = events[-1]
    assert "energy" in fields
    assert "coherence" in fields
    assert "lambda_mean" in fields


# ──────────────────────────────────────────────────────────────
# End-to-End Continuity Test
# ──────────────────────────────────────────────────────────────
def test_combined_adaptive_wave_feedback(mock_record):
    """End-to-end feedback test linking λ updates with ψ evolution."""
    λ_engine = AdaptiveLawEngine()
    ψ_engine = WaveDiffEngine()

    ψ = np.outer(np.linspace(0, 1, 5), np.linspace(0, 1, 5))
    ψ_engine.register_field("ψ", ψ)
    ψ_engine.register_field("λ", np.ones_like(ψ))

    # Adaptive update + wave step cycle
    for i in range(3):
        λ_engine.update("law_A", deviation=0.05 * i)
        ψ_engine.step("ψ", "λ", dt=0.1)

    # Validate both domains emitted telemetry
    law_events = [ev for ev in mock_record if ev[0] == "law_weight_update"]
    wave_events = [ev for ev in mock_record if ev[0] == "wave_step"]

    assert law_events, "Missing adaptive law telemetry"
    assert wave_events, "Missing wave calculus telemetry"

    # Cross-domain continuity
    last_λ = law_events[-1][1]["new_weight"]
    last_E = wave_events[-1][1]["energy"]
    assert last_λ > 0
    assert last_E >= 0.0