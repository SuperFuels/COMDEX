from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_o21g_voice_requirements_include_tts_stt_and_multipart():
    text = read("backend/requirements-voice-local.txt")
    assert "kokoro" in text
    assert "soundfile" in text
    assert "faster-whisper" in text
    assert "python-multipart" in text


def test_o21g_smoke_helper_exists_and_checks_local_provider_status():
    text = read("scripts/aion_voice_smoke_test.py")
    assert "AION O21 local voice smoke test" in text
    assert "/api/aion/voice/providers" in text
    assert "/api/aion/voice/tts" in text
    assert '"provider": "kokoro"' in text
    assert "tts_provider" in text
    assert "elevenlabs" in text


def test_o21g_smoke_helper_accepts_base_url_and_text():
    text = read("scripts/aion_voice_smoke_test.py")
    assert "--base-url" in text
    assert "--text" in text
    assert "http://127.0.0.1:8080" in text


def test_o21g_api_has_all_voice_routes_declared():
    text = read("backend/modules/aion_voice/api.py")
    assert '@router.get("/providers")' in text
    assert '@router.post("/tts")' in text
    assert '"/api/aion/voice/stt"' in text
    assert "aion_voice_stt" in text


def test_o21g_main_duplicate_route_guard_includes_all_voice_paths():
    text = read("backend/main.py")
    assert "AION_VOICE_PROVIDER_ROUTE_PATHS" in text
    assert '"/api/aion/voice/tts"' in text
    assert '"/api/aion/voice/stt"' in text
    assert '"/api/aion/voice/providers"' in text
    assert "app.include_router(aion_voice_router)" in text


def test_o21g_no_default_paid_voice_path_in_router():
    text = read("backend/modules/aion_voice/voice_router.py")
    assert 'DEFAULT_TTS_PROVIDER = "kokoro"' in text
    assert 'AION_ALLOW_ELEVENLABS", False' in text
    assert 'AION_ALLOW_BROWSER_SPEECH", False' in text
    assert "silent_browser_fallback_allowed" in text
    assert "False" in text


def test_o21g_frontend_debug_surfaces_remain_available():
    text = read("desktop/mac/src/app.js")
    assert "__debugAionVoiceProviders" in text
    assert "__debugAionO21ELiveMicTranscript" in text
    assert "__debugAionO21FBusinessTwinVoiceAnswers" in text
    assert "Using local voice. No ElevenLabs credits required." in text
    assert "Business Twin voice answers" in text
