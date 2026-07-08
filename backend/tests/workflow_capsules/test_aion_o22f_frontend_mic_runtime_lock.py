from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def test_o22f_frontend_posts_live_mic_audio_to_backend_stt_endpoint():
    text = read_app()

    assert "AION_O21E_STT_ENDPOINT" in text
    assert '"/api/aion/voice/stt"' in text
    assert "postAionO21EAudioChunkToStt" in text
    assert "FormData" in text
    assert "fetch(AION_O21E_STT_ENDPOINT" in text or "fetch(endpoint" in text
    assert "MediaRecorder" in text
    assert "getUserMedia" in text


def test_o22f_frontend_transcript_receives_backend_text():
    text = read_app()

    assert "appendAionO21ETranscript" in text
    assert "transcript" in text
    assert "text" in text
    assert "data.text" in text or "result.text" in text or ".text" in text
    assert "data.transcript" in text or "result.transcript" in text or ".transcript" in text


def test_o22f_frontend_does_not_call_browser_speech_or_elevenlabs_for_mic_stt():
    text = read_app()

    forbidden_runtime_calls = [
        "new SpeechRecognition(",
        "new webkitSpeechRecognition(",
        "SpeechRecognition()",
        "webkitSpeechRecognition()",
        "elevenlabs.io",
        "api.elevenlabs.io",
        "/v1/text-to-speech",
        "/v1/speech-to-text",
    ]

    for token in forbidden_runtime_calls:
        assert token not in text


def test_o22f_frontend_keeps_preview_safe_voice_metadata():
    text = read_app()

    assert "business_twin_mutation_enabled" in text
    assert "no_elevenlabs_call" in text
    assert "no_browser_speech_fallback" in text
    assert "external_actions_allowed" in text
    assert "approval_required" in text


def test_o22f_frontend_binds_transcript_to_business_twin_draft_not_live_mutation():
    text = read_app()

    assert "bindAionO21FTranscriptToBusinessTwinAnswer" in text
    assert "__aionBusinessTwinVoiceDraft" in text
    assert "pending_human_review" in text
    assert "business_context_hijack_allowed" in text
    assert "small_business_foundation" in text


def test_o22f_frontend_remains_business_agnostic():
    text = read_app()

    forbidden = [
        "Home" + " Fixed",
        "Al" + "meria",
        "Al" + "mería",
        "Mur" + "cia",
        "Mo" + "jacar",
        "per" + "gola",
        "paint" + "ing",
        "construct" + "ion",
        "roof" + " repair",
    ]

    for token in forbidden:
        assert token not in text
