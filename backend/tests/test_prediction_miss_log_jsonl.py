import json
from pathlib import Path

def test_prediction_miss_log_jsonl(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("AION_FORECAST_MIN_CONF", "0.1")   # make it easy to trigger
    monkeypatch.setenv("AION_FORECAST_RHO_ERR", "0.05")
    monkeypatch.setenv("AION_FORECAST_SQI_ERR", "0.05")

    # Force CAU stable so confidence computes high-ish
    def fake_cau_state(goal="maintain_coherence"):
        return {
            "t": 0.0,
            "allow_learn": True,
            "deny_reason": None,
            "adr_active": False,
            "cooldown_s": 0,
            "S": 1.0,
            "H": 0.0,
            "Phi": 0.0,
            "goal": goal,
        }

    monkeypatch.setattr(
        "backend.modules.aion_cognition.cee_exercise_playback._cau_state",
        fake_cau_state,
        raising=False,
    )

    from backend.modules.aion_cognition.cee_exercise_playback import CEEPlayback

    p = CEEPlayback(mode="simulate")

    # Turn 1: forecast uses defaults 0.6/0.6, then we set resonance actual to far away
    ex1 = {"type": "flashcard", "prompt": "p1", "answer": "a1", "options": ["a1"], "resonance": {"rho": 0.95, "sqi": 0.95}}
    p.play_exercise(ex1)

    # Turn 2: should compare prev forecast vs actual (big error) and emit miss
    ex2 = {"type": "flashcard", "prompt": "p2", "answer": "a2", "options": ["a2"], "resonance": {"rho": 0.10, "sqi": 0.10}}
    p.play_exercise(ex2)

    miss_path = Path(tmp_path) / "telemetry" / "prediction_miss_log.jsonl"
    assert miss_path.exists()

    rows = [json.loads(line) for line in miss_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(r.get("schema") == "AION.PredictionMiss.v1" for r in rows)
    assert any(r.get("cause") == "prediction_miss" for r in rows)