from __future__ import annotations

import os

def test_wave_state_timestamp_deterministic(monkeypatch):
    monkeypatch.setenv("TESSARIS_DETERMINISTIC_TIME", "1")

    from backend.modules.glyphwave.core.wave_state import WaveState

    w = WaveState(wave_id="w1")
    assert w.timestamp == "0000-00-00T00:00:00Z"
