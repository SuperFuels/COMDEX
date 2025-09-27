import pytest
from unittest.mock import patch

from backend.modules.consciousness.prediction_engine import get_prediction_engine
from backend.config import SPE_AUTO_FUSE


def test_prediction_engine_attaches_sqi_and_logs(monkeypatch):
    engine = get_prediction_engine()

    # 🔹 Capture emitted payloads
    emitted = {}
    def fake_emit_qwave_beam_ff(source, payload, context=None):
        emitted.update(payload)
        return {"status": "ok"}
    monkeypatch.setattr(
        "backend.modules.consciousness.prediction_engine.emit_qwave_beam_ff",
        fake_emit_qwave_beam_ff
    )

    # 🔹 Capture metrics logging
    logged = {}
    def fake_record_sqi_score_event(container_id, glyph_id, drift, qscore, source):
        logged.update({
            "container_id": container_id,
            "glyph_id": glyph_id,
            "drift": drift,
            "qscore": qscore,
            "source": source
        })
    monkeypatch.setattr(
        "backend.modules.codex.codex_metrics.record_sqi_score_event",
        fake_record_sqi_score_event
    )

    # 🔹 Minimal fake container
    container = {
        "id": "test-container",
        "electrons": [
            {
                "meta": {"label": "e1"},
                "glyphs": [
                    {"type": "predictive", "value": "future-x", "confidence": 0.9}
                ]
            }
        ]
    }

    # 🔹 Run prediction
    result = engine.run_prediction_on_container(container)

    # ✅ Assert SQI scores exist in beam + metrics log
    assert emitted.get("drift") is not None
    assert emitted.get("qscore") is not None
    assert logged.get("drift") is not None
    assert logged.get("qscore") is not None
    assert result["electron_predictions"][0]["confidence"] == 0.9


# ✅ New test: exercise maybe_autofuse behavior
def test_maybe_autofuse(monkeypatch):
    from backend.modules.spe.spe_bridge import maybe_autofuse

    beams = [{"id": "b1"}, {"id": "b2"}]

    # Case 1: SPE_AUTO_FUSE = False → beams unchanged
    monkeypatch.setattr("backend.modules.spe.spe_bridge.SPE_AUTO_FUSE", False)
    result = maybe_autofuse(beams)
    assert result == beams  # unchanged

    # Case 2: SPE_AUTO_FUSE = True → should call recombine_from_beams
    recombined = [{"id": "recombined"}]
    monkeypatch.setattr("backend.modules.spe.spe_bridge.SPE_AUTO_FUSE", True)
    monkeypatch.setattr(
        "backend.modules.spe.spe_bridge.recombine_from_beams",
        lambda x: recombined
    )
    result = maybe_autofuse(beams)
    assert result == recombined