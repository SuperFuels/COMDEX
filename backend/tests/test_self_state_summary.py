# backend/tests/test_self_state_summary.py
from __future__ import annotations

import types

import backend.modules.aion_cognition.self_state as ss


def test_self_state_allowed(monkeypatch):
    def fake_state(goal="maintain_coherence"):
        return {"allow_learn": True, "S": "1.0", "H": "1e-9", "Phi": "-0.02", "goal": goal}

    monkeypatch.setattr(ss, "get_authority_state", fake_state)
    s = ss.self_state_summary(goal="maintain_coherence", max_len=200)
    assert "Learning allowed" in s
    assert "S=1.00" in s
    assert "Φ=" in s


def test_self_state_denied(monkeypatch):
    def fake_state(goal="maintain_coherence"):
        return {"allow_learn": False, "deny_reason": "LOW_STABILITY", "cooldown_s": 12, "goal": goal}

    monkeypatch.setattr(ss, "get_authority_state", fake_state)
    s = ss.self_state_summary(goal="maintain_coherence", max_len=200)
    assert "Learning denied" in s
    assert "LOW_STABILITY" in s
    assert "cooldown=12s" in s


def test_self_state_adr(monkeypatch):
    def fake_state(goal="maintain_coherence"):
        return {"allow_learn": False, "adr_active": True, "cooldown_s": 7, "goal": goal}

    monkeypatch.setattr(ss, "get_authority_state", fake_state)
    s = ss.self_state_summary(goal="maintain_coherence", max_len=200)
    assert "ADR active" in s
    assert "cooldown=7s" in s


def test_self_state_max_len(monkeypatch):
    def fake_state(goal="maintain_coherence"):
        return {"allow_learn": False, "deny_reason": "X" * 500, "cooldown_s": 0, "goal": goal}

    monkeypatch.setattr(ss, "get_authority_state", fake_state)
    s = ss.self_state_summary(goal="maintain_coherence", max_len=80)
    assert len(s) <= 80