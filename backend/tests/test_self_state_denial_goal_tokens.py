# backend/tests/test_self_state_denial_goal_tokens.py
from backend.modules.aion_cognition import self_state as ss

def test_self_state_denial_includes_goal_and_is_single_line(monkeypatch):
    def fake_get_authority_state(goal: str):
        return {
            "allow_learn": False,
            "deny_reason": "adr_active",
            "adr_active": False,
            "cooldown_s": 7,
            "S": 0.1,
            "H": 0.9,
            "Phi": 0.0,
        }

    monkeypatch.setattr(ss, "get_authority_state", fake_get_authority_state)

    s = ss.self_state_summary(goal="maintain_coherence")
    assert "\n" not in s
    assert "deny_learn=1" in s
    assert "goal=maintain_coherence" in s
    assert "deny_reason=adr_active" in s
    assert "cooldown_s=7" in s