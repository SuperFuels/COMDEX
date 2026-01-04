from __future__ import annotations

def test_wave_state_evolve_deterministic(monkeypatch):
    monkeypatch.setenv("TESSARIS_DETERMINISTIC_TIME", "1")

    from backend.modules.glyphwave.core.wave_state import WaveState

    w1 = WaveState(wave_id="w1")
    w2 = WaveState(wave_id="w1")

    # Run evolve once on each — should match exactly
    w1.evolve()
    w2.evolve()

    assert w1.phase == w2.phase
    assert w1.coherence == w2.coherence
    assert w1.entropy == w2.entropy
    assert w1.last_sqi_score == w2.last_sqi_score
    assert w1.timestamp == "0000-00-00T00:00:00Z"
    assert w2.timestamp == "0000-00-00T00:00:00Z"
