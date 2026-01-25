from __future__ import annotations

import json


def test_forecast_report_written_per_turn(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))

    # Force CAU stable so confidence becomes deterministic-ish
    import backend.modules.aion_cognition.cee_exercise_playback as pb

    def fake_cau(goal="maintain_coherence"):
        return {"allow_learn": True, "S": 0.9, "H": 0.1, "Phi": 0.0, "deny_reason": None, "adr_active": False, "cooldown_s": 0}

    monkeypatch.setattr(pb, "_cau_state", fake_cau, raising=False)

    player = pb.CEEPlayback(mode="simulate")
    player.play_exercise(
        {
            "type": "flashcard",
            "prompt": "p",
            "options": ["a", "b"],
            "answer": "a",
            "resonance": {"rho": 0.7, "Ibar": 0.6, "sqi": 0.8},
        }
    )

    p = tmp_path / "telemetry" / "forecast_report.jsonl"
    assert p.exists()

    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) >= 1

    r = rows[-1]
    assert r["schema"] == "AION.Forecast.v1"
    assert r["session"] == player.session_id
    assert "goal" in r and "rho_next" in r and "sqi_next" in r and "confidence" in r