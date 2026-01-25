# backend/tests/test_goal_transition_contradiction.py
from __future__ import annotations

import json
from pathlib import Path


def _read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def test_goal_transition_contradiction_to_resolve_conflict(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("CEE_LEX_AUTO_CORRECT", "0")
    monkeypatch.setenv("AION_COMMENTARY", "0")
    monkeypatch.setenv("AION_VERBOSITY", "off")

    # CAU stable + allow learn, so CAU won’t force coherence / deny
    import backend.modules.aion_cognition.cee_exercise_playback as m

    def _fake_cau(goal="maintain_coherence"):
        return {
            "allow_learn": True,
            "deny_reason": None,
            "adr_active": False,
            "cooldown_s": 0,
            "S": 1.0,
            "H": 0.0,
            "Phi": 0.0,
            "goal": goal,
        }

    monkeypatch.setattr(m, "_cau_state", _fake_cau, raising=False)

    # Force a “memory recall” answer that contradicts the exercise answer
    monkeypatch.setattr(
        m,
        "recall_from_memory",
        lambda _prompt: {"answer": "MEM_ANSWER"},
        raising=True,
    )

    p = m.CEEPlayback(mode="simulate")
    ex = {
        "type": "flashcard",
        "prompt": "What is 2+2?",
        "answer": "4",  # contradicts MEM_ANSWER
        "options": ["3", "4", "5"],
        "resonance": {"rho": 0.6, "Ibar": 0.6, "sqi": 0.6},
    }

    p.play_exercise(ex)

    log_path = tmp_path / "telemetry" / "goal_transition_log.jsonl"
    rows = _read_jsonl(log_path)

    assert any(
        r.get("schema") == "AION.GoalTransition.v1"
        and r.get("cause") == "contradiction"
        and r.get("to_goal") == "resolve_conflict"
        for r in rows
    ), rows