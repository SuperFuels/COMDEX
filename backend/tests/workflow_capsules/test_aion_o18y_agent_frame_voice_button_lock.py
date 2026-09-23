from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o18y_agent_frame_voice_button_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18Y AGENT FRAME VOICE BUTTON LOCK" in text
    assert "aion-o18y-agent-frame-voice-button-style" in text
    assert "__debugAionO18YAgentFrameVoiceButton" in text
    assert "data-aion-o18y-agent-frame-voice" in text

def test_o18y_uses_existing_o18x_voice_handler():
    text = APP.read_text(encoding="utf-8")
    assert "clickExistingVoiceO18Y" in text
    assert "data-aion-o18x-voice" in text
    assert "data-aion-o18x-voice-answer" in text
    assert "button_inside_agent_frame" in text
