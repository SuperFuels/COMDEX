from __future__ import annotations

from typing import Any, Dict, Iterator, List

import backend.modules.aion_cognition.correction_history as ch


PROMPT = "Select the synonym of 'calm'"


def _mk_row(ts: float, *, correct: bool, guess: str | None, answer: str | None) -> Dict[str, Any]:
    return {
        "ts": ts,
        "session": "PLAY-TEST",
        "mode": "simulate",
        "type": "find_match",
        "prompt": PROMPT,
        "intent": "recall",
        "coherence": 1.0,
        "correct": correct,
        "guess": guess,
        "answer": answer,
        "allow_learn": True,
        "deny_reason": None,
        "adr_active": False,
        "cooldown_s": 0,
        "S": 1.0,
        "H": 0.0,
        "Phi": 0.0,
        "response_time_ms": 1,
        "schema": "AION.TurnLog.v1",
    }


def test_since_ts_filters_out_older_event(monkeypatch):
    # Force fallback to TurnLog (no LexMemory events)
    monkeypatch.setattr(ch, "_load_json", lambda _p: None)

    # TurnLog fixture: 3 mismatches at ts=10,20,30
    rows: List[Dict[str, Any]] = [
        _mk_row(10.0, correct=False, guess="angry", answer="peaceful"),
        _mk_row(20.0, correct=False, guess="angry", answer="peaceful"),
        _mk_row(30.0, correct=False, guess="angry", answer="peaceful"),
    ]

    def _iter(_: Any) -> Iterator[Dict[str, Any]]:
        yield from rows

    monkeypatch.setattr(ch, "_iter_jsonl", _iter)

    evs = ch.get_correction_history(PROMPT, limit=50, since_ts=25.0, until_ts=None)

    # Only ts >= 25 should remain (i.e., 30)
    assert [e["t"] for e in evs] == [30.0]
    assert evs[0]["cause"] == "turnlog_mismatch"
    assert evs[0]["source"] == "turn_log"


def test_until_ts_filters_out_newer_event(monkeypatch):
    monkeypatch.setattr(ch, "_load_json", lambda _p: None)

    rows: List[Dict[str, Any]] = [
        _mk_row(10.0, correct=False, guess="angry", answer="peaceful"),
        _mk_row(20.0, correct=False, guess="angry", answer="peaceful"),
        _mk_row(30.0, correct=False, guess="angry", answer="peaceful"),
    ]

    def _iter(_: Any) -> Iterator[Dict[str, Any]]:
        yield from rows

    monkeypatch.setattr(ch, "_iter_jsonl", _iter)

    evs = ch.get_correction_history(PROMPT, limit=50, since_ts=None, until_ts=15.0)

    # Only ts <= 15 should remain (i.e., 10)
    assert [e["t"] for e in evs] == [10.0]
    assert evs[0]["cause"] == "turnlog_mismatch"
    assert evs[0]["source"] == "turn_log"

def test_time_window_bounds_are_inclusive(monkeypatch):
    monkeypatch.setattr(ch, "_load_json", lambda _p: None)

    rows: List[Dict[str, Any]] = [
        _mk_row(10.0, correct=False, guess="angry", answer="peaceful"),
        _mk_row(20.0, correct=False, guess="angry", answer="peaceful"),
        _mk_row(30.0, correct=False, guess="angry", answer="peaceful"),
    ]

    def _iter(_: Any) -> Iterator[Dict[str, Any]]:
        yield from rows

    monkeypatch.setattr(ch, "_iter_jsonl", _iter)

    # inclusive: since_ts == 20 keeps 20
    evs1 = ch.get_correction_history(PROMPT, limit=50, since_ts=20.0, until_ts=None)
    assert [e["t"] for e in evs1] == [30.0, 20.0]

    # inclusive: until_ts == 20 keeps 20
    evs2 = ch.get_correction_history(PROMPT, limit=50, since_ts=None, until_ts=20.0)
    assert [e["t"] for e in evs2] == [20.0, 10.0]

    # inclusive window: exact match keeps exactly that incident
    evs3 = ch.get_correction_history(PROMPT, limit=50, since_ts=20.0, until_ts=20.0)
    assert [e["t"] for e in evs3] == [20.0]