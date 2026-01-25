from __future__ import annotations

import json
from pathlib import Path


def test_goal_transition_log_respects_data_root(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))

    from backend.modules.aion_cognition.goal_transitions import log_goal_transition

    log_goal_transition(
        ts=123.0,
        from_goal="maintain_coherence",
        to_goal="improve_accuracy",
        cause="unit_test",
        session="TEST-1",
    )

    p = tmp_path / "telemetry" / "goal_transition_log.jsonl"
    assert p.exists()

    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert any(r.get("session") == "TEST-1" and r.get("cause") == "unit_test" for r in rows)