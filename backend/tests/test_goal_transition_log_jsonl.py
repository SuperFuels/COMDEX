# backend/tests/test_goal_transition_log_jsonl.py
from __future__ import annotations

import json
from pathlib import Path

from backend.modules.aion_cognition.goal_transitions import log_goal_transition


def test_goal_transition_writes_jsonl_line(tmp_path, monkeypatch):
    # Force DATA_ROOT so the logger writes into a temp folder
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))

    log_goal_transition(
        ts=123.456,
        from_goal="maintain_coherence",
        to_goal="improve_accuracy",
        cause="test",
        session="PLAY-TEST",
    )

    p = tmp_path / "telemetry" / "goal_transition_log.jsonl"
    assert p.exists()

    lines = p.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 1

    rec = json.loads(lines[-1])
    assert rec.get("schema") == "AION.GoalTransition.v1"
    assert rec.get("ts") == 123.456
    assert rec.get("from_goal") == "maintain_coherence"
    assert rec.get("to_goal") == "improve_accuracy"
    assert rec.get("cause") == "test"
    assert rec.get("session") == "PLAY-TEST"