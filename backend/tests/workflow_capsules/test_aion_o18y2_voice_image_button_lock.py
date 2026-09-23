from pathlib import Path

APP = Path("desktop/mac/src/app.js")
VOICE = Path("desktop/mac/src/assets/voice.png")

def test_o18y2_voice_image_asset_exists():
    assert VOICE.exists()
    assert VOICE.stat().st_size > 0

def test_o18y2_voice_image_button_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18Y2 VOICE IMAGE BUTTON LOCK" in text
    assert "aion-o18y2-voice-image-button-style" in text
    assert "__debugAionO18Y2VoiceImageButton" in text
    assert "./assets/voice.png" in text
    assert "data-aion-o18y2-voice-img" in text

def test_o18y2_targets_agent_and_terminal_voice_buttons():
    text = APP.read_text(encoding="utf-8")
    assert "data-aion-o18y-agent-frame-voice" in text
    assert "data-aion-o18x-voice" in text
    assert "data-aion-o18x-voice-answer" in text
    assert "agent_button_has_image" in text
