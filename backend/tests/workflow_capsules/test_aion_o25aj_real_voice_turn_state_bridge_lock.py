from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app():
    return APP.read_text(encoding="utf-8")


def test_o25aj_real_voice_turn_state_is_installed():
    text = read_app()
    assert "BEGIN AION O25AJ REAL VOICE TURN STATE BRIDGE LOCK" in text
    assert "__debugAionO25AJRealVoiceTurnStateBridge" in text
    assert "window.handleAionO25EUserAnswerTurn" in text
    assert "speakNextQuestionFromPacketO25AJ(packet)" in text


def test_o25e_no_longer_prerenders_opening_in_transcript_rows():
    text = read_app()
    start = text.index("function getO25ETranscriptRows()")
    end = text.index("function renderAionO25ETerminalOnlyVoiceConversation()", start)
    block = text[start:end]

    assert "transcriptRows.push({\n      speaker: \"AION\"" not in block
    assert "getO25EConversationState()" in text
    assert "appendO25EConversationRow" in text


def test_o25e_typed_submit_uses_real_turn_handler():
    text = read_app()
    start = text.index("function handleO25ETypedSubmit(event)")
    end = text.index("function installO25EStyles()", start)
    block = text[start:end]

    assert "window.handleAionO25EUserAnswerTurn(text" in block
    assert "source: \"typed_fallback\"" in block


def test_o25aj_does_not_pretend_fallback_is_controller_generated():
    text = read_app()
    assert "version: \"aion.o25aj.frontend_schema_prompt_fallback\"" in text
    assert "fallback: true" in text
    assert "schema_driven: false" in text
    assert "fallback_next_question" in text


def test_o25ad_static_fallback_terminal_does_not_seed_aion_message():
    text = read_app()
    assert '<div class="aion-o25e-transcript" data-aion-o25e-transcript-log="true"></div>' in text
