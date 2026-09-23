from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_o21h_lock_document_exists_and_names_full_chain():
    text = read("docs/aion/voice/aion_o21_local_voice_stack_lock.md")
    assert "AION-O21-LOCAL-FIRST-VOICE-STACK" in text
    assert "O21A" in text
    assert "O21B" in text
    assert "O21C" in text
    assert "O21D" in text
    assert "O21E" in text
    assert "O21F" in text
    assert "O21G" in text
    assert "O21H" in text


def test_o21h_lock_document_states_default_voice_policy():
    text = read("docs/aion/voice/aion_o21_local_voice_stack_lock.md")
    assert "ElevenLabs is no longer the default" in text
    assert "AION_TTS_PROVIDER=kokoro" in text
    assert "AION_STT_PROVIDER=faster_whisper" in text
    assert "AION_ALLOW_ELEVENLABS=false" in text
    assert "AION_ALLOW_BROWSER_SPEECH=false" in text


def test_o21h_backend_routes_are_locked():
    text = read("backend/modules/aion_voice/api.py")
    assert '@router.get("/providers")' in text
    assert '@router.post("/tts")' in text
    assert '"/api/aion/voice/stt"' in text


def test_o21h_router_default_is_local_first_and_no_silent_fallback():
    text = read("backend/modules/aion_voice/voice_router.py")
    assert 'DEFAULT_TTS_PROVIDER = "kokoro"' in text
    assert 'DEFAULT_STT_PROVIDER = "faster_whisper"' in text
    assert 'AION_ALLOW_ELEVENLABS", False' in text
    assert 'AION_ALLOW_BROWSER_SPEECH", False' in text
    assert "silent_browser_fallback_allowed" in text


def test_o21h_local_tts_and_stt_providers_exist():
    kokoro = read("backend/modules/aion_voice/providers/kokoro_tts.py")
    whisper = read("backend/modules/aion_voice/providers/faster_whisper_stt.py")
    assert "synthesize_with_kokoro" in kokoro
    assert "KPipeline" in kokoro
    assert "transcribe_audio_bytes" in whisper
    assert "WhisperModel" in whisper


def test_o21h_frontend_debug_and_binding_surfaces_exist():
    text = read("desktop/mac/src/app.js")
    assert "__debugAionVoiceProviders" in text
    assert "__debugAionO21ELiveMicTranscript" in text
    assert "__debugAionO21FBusinessTwinVoiceAnswers" in text
    assert "small_business_foundation" in text
    assert "business_context_hijack_allowed: false" in text


def test_o21h_requirements_and_smoke_helper_exist():
    requirements = read("backend/requirements-voice-local.txt")
    smoke = read("scripts/aion_voice_smoke_test.py")
    assert "kokoro" in requirements
    assert "faster-whisper" in requirements
    assert "python-multipart" in requirements
    assert "/api/aion/voice/providers" in smoke
    assert "/api/aion/voice/tts" in smoke

def test_o21h_no_business_specific_hardcoded_answers_or_industry_terms():
    scanned_files = [
        "desktop/mac/src/app.js",
        "docs/aion/voice/aion_o21_local_voice_stack_lock.md",
        "backend/tests/workflow_capsules/test_aion_o21f_business_twin_voice_answer_binding_lock.py",
    ]

    forbidden = [
        "Home" + " Fixed",
        "Example" + " Business",
        "Al" + "meria",
        "Al" + "mería",
        "Mur" + "cia",
        "Mo" + "jacar",
        "Mo" + "jácar",
        "per" + "gola",
        "per" + "golas",
        "paint" + "ing",
        "construct" + "ion",
        "Home" + " Repairs",
        "roof" + " repair",
        "villa" + " painting",
        "My business is Home",
        "We offer example",
    ]

    for rel in scanned_files:
        content = read(rel)
        for token in forbidden:
            assert token not in content, f"{token!r} must not be hardcoded in {rel}"


def test_o21h_voice_binding_reads_runtime_transcript_not_fixed_answer():
    text = read("desktop/mac/src/app.js")
    assert "bindAionO21FTranscriptToBusinessTwinAnswer" in text
    assert "runtimeTranscriptText" not in text or "bindAionO21FTranscriptToBusinessTwinAnswer(runtimeTranscriptText)" in text
    assert 'bindAionO21FTranscriptToBusinessTwinAnswer("My business is' not in text
    assert "business_context_hijack_allowed: false" in text
    assert "AION_O21F_STARTUP_ROUTE = \"small_business_foundation\"" in text

