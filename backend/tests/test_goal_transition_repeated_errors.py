# backend/tests/test_goal_transition_repeated_errors.py
from __future__ import annotations

import importlib
import json
from pathlib import Path


def test_goal_transition_repeated_errors(tmp_path, monkeypatch):
    # Isolate all file IO under tmp DATA_ROOT
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))

    # Reload modules so any DATA_ROOT-aware paths bind to tmp_path
    import backend.modules.aion_cognition.goal_transitions as goal_transitions
    import backend.modules.aion_cognition.cee_exercise_playback as cee

    importlib.reload(goal_transitions)
    importlib.reload(cee)

    # CAU stub: always allow learn, but NOT "stable enough" to trigger cau_update -> improve_accuracy
    def _stub_cau_state(goal: str = "maintain_coherence"):
        return {
            "t": 0.0,
            "allow_learn": True,
            "deny_reason": None,
            "adr_active": False,
            "cooldown_s": 0,
            "S": 0.50,   # keep below 0.85
            "H": 0.50,   # keep above 0.15
            "Phi": 0.0,
            "goal": goal,
            "source": "TEST_STUB",
        }

    # Patch the playback module's CAU function (it caches at import as _cau_state)
    monkeypatch.setattr(cee, "_cau_state", _stub_cau_state, raising=True)

    # Patch recall so we can force 3 wrong out of 6 deterministically in simulate mode
    wrong_prompts = {"p1", "p2", "p3"}

    def _stub_recall_from_memory(prompt: str):
        p = (prompt or "").strip()
        if p in wrong_prompts:
            return {"answer": "WRONG"}  # will not match ex["answer"]
        return None  # fall back to simulate guess=answer -> correct

    monkeypatch.setattr(cee, "recall_from_memory", _stub_recall_from_memory, raising=True)

    # Run 6 exercises: first 3 wrong via memory recall, next 3 correct via simulate fallback
    player = cee.CEEPlayback(mode="simulate")
    # ensure recent window exists even if you forgot to add it yet
    if not hasattr(player, "_recent_correct"):
        player._recent_correct = []

    for i in range(1, 7):
        player.play_exercise(
            {
                "type": "flashcard",
                "prompt": f"p{i}",
                "answer": "RIGHT",
                "options": ["RIGHT", "WRONG"],
                "resonance": {"rho": 0.6, "Ibar": 0.6, "sqi": 0.6},
            }
        )

    # Assert we logged a repeated_errors transition to improve_accuracy
    log_path = tmp_path / "telemetry" / "goal_transition_log.jsonl"
    assert log_path.exists(), "goal_transition_log.jsonl was not created"

    rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(
        r.get("cause") == "repeated_errors" and r.get("to_goal") == "improve_accuracy"
        for r in rows
    ), f"Expected repeated_errors -> improve_accuracy transition, got: {rows}"