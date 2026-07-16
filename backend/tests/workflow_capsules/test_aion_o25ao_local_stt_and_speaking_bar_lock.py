from pathlib import Path

APP = Path("desktop/mac/src/app.js")
REQUIREMENTS = Path("backend/requirements-voice-local.txt")


def read_app():
    return APP.read_text(encoding="utf-8")


def test_o25ao_local_stt_dependency_is_declared():
    text = REQUIREMENTS.read_text(encoding="utf-8")
    assert "faster-whisper" in text


def test_o25ao_terminal_reads_conversation_speaking_state():
    text = read_app()
    start = text.index("function renderAionO25ETerminalOnlyVoiceConversation")
    end = text.index("function syncAionO25ETerminalOnlyVoiceConversation", start)
    block = text[start:end]

    assert "const conversation = getO25EConversationState();" in block
    assert 'const speaking = conversation.status === "speaking";' in block
    assert "const voiceActive = recording || speaking;" in block


def test_o25ao_bar_animates_for_aion_speaking_or_user_recording():
    text = read_app()
    start = text.index("function renderAionO25ETerminalOnlyVoiceConversation")
    end = text.index("function syncAionO25ETerminalOnlyVoiceConversation", start)
    block = text[start:end]

    assert '${voiceActive ? "is-active" : ""}' in block
    assert 'data-aion-o25e-voice-activity=' in block
    assert '"speaking"' in block
    assert '"listening"' in block


def test_o25ao_existing_single_toggle_is_preserved():
    text = read_app()
    start = text.index("function renderAionO25ETerminalOnlyVoiceConversation")
    end = text.index("function syncAionO25ETerminalOnlyVoiceConversation", start)
    block = text[start:end]

    assert block.count('data-aion-o25e-talk-toggle="true"') == 1
    assert "Stop talking" in block
    assert "Reply to AION" in block
