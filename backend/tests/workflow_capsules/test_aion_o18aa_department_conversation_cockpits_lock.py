from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o18aa_department_conversation_cockpits_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18AA DEPARTMENT CONVERSATION COCKPITS LOCK" in text
    assert "O18AA department conversation cockpits installed" in text
    assert "__debugAionO18AADepartmentConversationCockpits" in text
    assert "renderLiveAgentsWorkspaceBodyWithDepartmentConversationCockpitsO18AA" in text

def test_o18aa_supports_core_departments():
    text = APP.read_text(encoding="utf-8")
    assert '"sales"' in text
    assert '"finance"' in text
    assert '"operations"' in text
    assert '"support"' in text
    assert "Sales assignment package" in text
    assert "Finance assignment package" in text
    assert "Operations assignment package" in text
    assert "Support assignment package" in text

def test_o18aa_terminal_and_voice_contract():
    text = APP.read_text(encoding="utf-8")
    assert "data-aion-o18aa-terminal" in text
    assert "data-aion-o18aa-agent-frame" in text
    assert "data-aion-o18aa-agent-mount" in text
    assert "data-aion-o18aa-voice-button" in text
    assert "SpeechRecognition" in text
    assert "Every question and answer is recorded in this terminal" in text
