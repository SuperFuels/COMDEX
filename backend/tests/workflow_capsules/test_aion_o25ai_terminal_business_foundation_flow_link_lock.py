from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CONTROLLER = Path("desktop/mac/src/aion_business_foundation_voice_controller.js")


def read_app():
    return APP.read_text(encoding="utf-8")


def read_controller():
    return CONTROLLER.read_text(encoding="utf-8")


def test_o25ai_bad_overlay_and_wrong_combined_prompt_removed():
    text = read_app()
    assert "BEGIN AION O25AH TERMINAL OPENING SCRIPT CLEAN LOCK" not in text
    assert "window.__aionO25AHCanonicalOpening" not in text
    assert "What are you looking to achieve? Before we start, what should I call you?" not in text
    assert "o25ab_selected_terminal_intro_fallback" not in text


def test_o25ai_terminal_uses_current_o25aj_opening_authority():
    text = read_app()
    assert 'const AION_O25AJ_OPENING = "Hi, I’m AION, your AI business partner.' in text
    assert 'Before we start, what should I call you?";' in text
    assert "function startAionO25ABSelectedTerminalVoiceO25AJ" in text
    assert "o25aj_terminal_opening" in text


def test_o25ai_answer_links_to_business_foundation_packet():
    text = read_app()
    assert "applyAnswerToFoundationO25AJ" in text
    assert "window.applyAionO25BVoiceTurnToFoundationDraft" in text
    assert "window.__aionBusinessFoundationVoiceDiscoveryPacket = packet" in text
    assert "__debugAionO25AJRealVoiceTurnStateBridge" in text
    assert "speaker: \"user\"" in text
    assert "role: \"user\"" in text


def test_o25ai_current_question_target_field_is_passed_to_controller():
    text = read_app()
    controller = read_controller()
    assert "target_field" in text
    assert "current_question_answer" in controller
    assert "last_turn" in controller
    assert "transcript_count" in controller


def test_o25ai_aion_prompt_not_piped_as_user_stt():
    text = read_app()
    assert 'speaker: "AION"' in text
    assert 'speaker: "You"' in text
    assert "looksAion" in text
    assert "aion_intro_as_user_visible" in text
