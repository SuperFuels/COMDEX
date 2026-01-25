from backend.modules.aion_cognition.denial_explain import denial_explanation_line

def test_denial_explanation_includes_goal_and_is_single_line():
    s = denial_explanation_line(goal="maintain_coherence", deny_reason="adr_active")
    assert "goal=maintain_coherence" in s
    assert "deny_learn=1" in s
    assert "deny_reason=adr_active" in s
    assert "\n" not in s
    assert "\r" not in s