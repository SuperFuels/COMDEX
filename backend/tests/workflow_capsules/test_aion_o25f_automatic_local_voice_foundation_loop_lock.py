from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"


def text():
    return APP.read_text(encoding="utf-8")


def o25f_block():
    data = text()
    start = data.index("AION O25F — Automatic Local Voice Business Foundation Conversation Loop")
    end = data.index('console.log("[AION] O25F automatic local voice foundation conversation installed");', start)
    return data[start:end]


def test_o25f_uses_absolute_local_stt_endpoint_not_file_relative():
    data = text()
    assert 'const AION_O21E_STT_ENDPOINT = "http://127.0.0.1:8080/api/aion/voice/stt";' in data
    assert 'fetch(AION_O21E_STT_ENDPOINT' in data


def test_o25f_auto_speaks_after_i_have_a_business_click():
    block = o25f_block()
    assert "data-aion-o20c-open-conversation" in block
    assert "beginAionO25FAutomaticConversation" in block
    assert "speakAion" in block
    assert "OPENING_INTRO_EXISTING_BUSINESS" in block
    assert "What is the business called" in block


def test_o25f_clears_stale_conversation_on_fresh_launch():
    block = o25f_block()
    assert "clearStaleConversationOpenOnFreshLaunch" in block
    assert "SESSION_OPEN_KEY" in block
    assert 'aion.o20c.conversationOpen' in block
    assert "removeItem(STORAGE_OPEN_KEY)" in block


def test_o25f_transcript_is_product_surface_and_hidden_panels_stay_hidden():
    block = o25f_block()
    assert 'data-aion-o25f-auto-voice-terminal="true"' in block
    assert 'data-aion-o25f-transcript="true"' in block
    assert "Reply to AION" in block
    assert "Stop talking" in block
    assert "Business Foundation draft" in block
    assert "Foundation readiness" not in block
    assert "Pending review" not in block
    assert "Business Twin mutation" not in block


def test_o25f_next_question_is_schema_driven_not_hardcoded_answers():
    block = o25f_block()
    assert "extractNextQuestion" in block
    assert "buildAionO25BNextBestFoundationQuestion" in block
    assert "queueNextQuestionAfterUserTurn" in block
    assert "appendAionO25FAutoQuestionTranscript" in block
    forbidden = ["roofing/leaks", "painting/rendering", "home_fixed", "costa-conexion"]
    lowered = block.lower()
    for token in forbidden:
        assert token not in lowered


def test_o25f_debug_hook_exists():
    block = o25f_block()
    assert "__debugAionO25FAutomaticLocalVoiceFoundationConversation" in block
    assert "stt_endpoint_absolute: true" in block
    assert "transcript_auto_question_patched" in block


def test_o25f_syntax_clean():
    subprocess.run(["node", "--check", str(APP)], cwd=ROOT, check=True)
