from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CONTROLLER = Path("desktop/mac/src/aion_business_foundation_voice_controller.js")


def read_app():
    return APP.read_text(encoding="utf-8")


def read_controller():
    return CONTROLLER.read_text(encoding="utf-8")


def test_o25f_uses_absolute_local_stt_endpoint_not_file_relative():
    text = read_app()
    assert 'const AION_O21E_STT_ENDPOINT = "http://127.0.0.1:8080/api/aion/voice/stt";' in text
    assert 'const AION_O21E_STT_ENDPOINT = "/api/aion/voice/stt";' not in text


def test_o25f_voice_loop_is_now_o25aj_single_runtime_authority():
    text = read_app()
    assert "BEGIN AION O25AJ REAL VOICE TURN STATE BRIDGE LOCK" in text
    assert "window.startAionO25ABSelectedTerminalVoice = function startAionO25ABSelectedTerminalVoiceO25AJ" in text
    assert "window.handleAionO25EUserAnswerTurn" in text
    assert "speakNextQuestionFromPacketO25AJ" in text


def test_o25f_auto_speaks_after_i_have_a_business_click_via_selected_terminal():
    text = read_app()
    assert "openBusinessTerminal" in text
    assert "startAionO25ABSelectedTerminalVoice" in text
    assert "o25aj_terminal_opening" in text


def test_o25f_transcript_is_product_surface_not_hidden_old_panels():
    text = read_app()
    assert 'data-aion-o25e-voice-terminal-only="true"' in text
    assert 'data-aion-o25e-transcript-log="true"' in text
    assert "[data-aion-o25e-voice-terminal-only='true'] [data-aion-o21f-business-twin-voice-binding]" in text


def test_o25f_next_question_is_schema_driven_from_o25b_controller():
    app = read_app()
    controller = read_controller()
    assert "applyAionO25BVoiceTurnToFoundationDraft" in app
    assert "buildAionO25BNextBestFoundationQuestion" in controller
    assert "schema_driven: true" in controller
    assert "target_field" in controller
    assert "current_question_answer" in controller


def test_o25f_debug_hook_exists_on_current_authority():
    text = read_app()
    assert "__debugAionO25AJRealVoiceTurnStateBridge" in text
    assert "__debugAionO25ETerminalOnlyFoundationVoiceUX" in text


def test_o25f_no_live_execution_or_external_side_effects():
    text = read_app()
    assert "external_actions_allowed: false" in text
    assert "live_execution_allowed: false" in text
