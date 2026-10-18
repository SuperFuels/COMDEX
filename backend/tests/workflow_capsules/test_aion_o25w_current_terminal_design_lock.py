from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"


def app_text():
    return APP.read_text(encoding="utf-8")


def function_block(name: str) -> str:
    text = app_text()
    start = text.index(f"function {name}(")
    brace = text.index("{", start)
    depth = 0
    for idx in range(brace, len(text)):
        char = text[idx]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]
    raise AssertionError(f"Could not slice {name}")


def test_o25w_current_terminal_uses_proper_voice_conversation_design():
    block = function_block("renderCurrentTerminal")

    assert "AION O25W" in block
    assert "AION voice conversation" in block
    assert "Business Foundation Conversation" in block
    assert "data-aion-o25w-current-terminal" in block
    assert "data-aion-o25w-transcript" in block
    assert "Local Kokoro voice" in block


def test_o25w_keeps_working_voice_handlers():
    block = function_block("renderCurrentTerminal")

    assert 'data-aion-o25f-reply="true"' in block
    assert 'data-aion-o25f-stop="true"' in block
    assert 'data-aion-o25f-typed-form="true"' in block
    assert 'data-aion-o25f-typed-input="true"' in block


def test_o25w_does_not_restore_legacy_opener_into_current_terminal():
    block = function_block("renderCurrentTerminal")

    assert "Tessaris Voice Opener" not in block
    assert "data-aion-o19i-voice-guide-panel" not in block
    assert "ElevenLabs" not in block
