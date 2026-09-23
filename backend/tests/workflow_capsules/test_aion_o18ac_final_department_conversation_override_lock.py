from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o18ac_final_override_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18AC FINAL DEPARTMENT CONVERSATION OVERRIDE LOCK" in text
    assert "renderLiveAgentsWorkspaceBodyWithFinalDepartmentConversationO18AC" in text
    assert "__debugAionO18ACFinalDepartmentConversationOverride" in text
    assert "__aionO18ACWrapped" in text

def test_o18ac_departments_present():
    text = APP.read_text(encoding="utf-8")
    for dept in ["sales", "finance", "operations", "support"]:
        assert f"{dept}:" in text
        assert f"{dept}_pilot" in text

def test_o18ac_terminal_contract():
    text = APP.read_text(encoding="utf-8")
    assert "AI PUSHBACK / DISCOVERY GATE" in text
    assert "DISCOVERY QUESTION INBOX" in text
    assert "data-aion-o18ac-voice" in text
    assert "data-aion-o18ac-input" in text
    assert "Boardroom Package" in text
