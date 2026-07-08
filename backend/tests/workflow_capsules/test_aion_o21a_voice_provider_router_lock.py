from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_o21a_voice_router_files_exist():
    required = [
        "backend/modules/aion_voice/__init__.py",
        "backend/modules/aion_voice/schemas.py",
        "backend/modules/aion_voice/voice_router.py",
        "backend/modules/aion_voice/api.py",
        "backend/modules/aion_voice/providers/__init__.py",
        "backend/modules/aion_voice/providers/kokoro_tts.py",
        "backend/modules/aion_voice/providers/elevenlabs_tts.py",
        "backend/modules/aion_voice/providers/browser_fallback.py",
    ]
    for rel in required:
        assert (ROOT / rel).exists(), rel


def test_o21a_default_provider_is_kokoro_and_stt_is_faster_whisper():
    text = read("backend/modules/aion_voice/voice_router.py")
    assert 'DEFAULT_TTS_PROVIDER = "kokoro"' in text
    assert 'DEFAULT_STT_PROVIDER = "faster_whisper"' in text
    assert "AION_TTS_PROVIDER" in text
    assert "AION_STT_PROVIDER" in text


def test_o21a_elevenlabs_disabled_by_default():
    text = read("backend/modules/aion_voice/voice_router.py")
    assert 'AION_ALLOW_ELEVENLABS", False' in text
    assert "synthesize_with_elevenlabs" in text

    provider = read("backend/modules/aion_voice/providers/elevenlabs_tts.py")
    assert "elevenlabs_disabled" in provider
    assert "would_call_elevenlabs" in provider
    assert "False" in provider


def test_o21a_browser_speech_disabled_and_not_silent():
    text = read("backend/modules/aion_voice/voice_router.py")
    assert 'AION_ALLOW_BROWSER_SPEECH", False' in text
    assert "silent_browser_fallback_allowed" in text
    assert "False" in text

    provider = read("backend/modules/aion_voice/providers/browser_fallback.py")
    assert "browser_speech_disabled" in provider
    assert "silent_fallback_allowed" in provider
    assert "False" in provider


def test_o21a_kokoro_is_local_default_provider_file():
    provider = read("backend/modules/aion_voice/providers/kokoro_tts.py")
    assert "KOKORO_PROVIDER_ID" in provider
    assert "synthesize_with_kokoro" in provider
    assert "x-aion-voice-provider" in provider
    assert "x-aion-voice-local" in provider
    assert "fallback=\"none\"" in provider


def test_o21a_router_returns_structured_failure_json_contract():
    schemas = read("backend/modules/aion_voice/schemas.py")
    assert "class VoiceResult" in schemas
    assert "def to_json" in schemas
    assert '"ok"' in schemas
    assert '"provider"' in schemas
    assert '"reason"' in schemas
    assert '"fallback"' in schemas


def test_o21a_api_keeps_tts_endpoint_and_adds_provider_status():
    api = read("backend/modules/aion_voice/api.py")
    assert 'prefix="/api/aion/voice"' in api
    assert '@router.post("/tts")' in api
    assert '@router.get("/providers")' in api
    assert "synthesize_text" in api
    assert "get_voice_provider_status" in api


def test_o21a_runtime_router_behaviour(monkeypatch):
    from backend.modules.aion_voice.voice_router import get_voice_provider_status, synthesize_text

    monkeypatch.delenv("AION_TTS_PROVIDER", raising=False)
    monkeypatch.delenv("AION_ALLOW_ELEVENLABS", raising=False)
    monkeypatch.delenv("AION_ALLOW_BROWSER_SPEECH", raising=False)
    monkeypatch.delenv("AION_LOCAL_VOICE_ENABLED", raising=False)

    status = get_voice_provider_status()
    assert status["tts_provider"] == "kokoro"
    assert status["stt_provider"] == "faster_whisper"
    assert status["elevenlabs_enabled"] is False
    assert status["browser_fallback_enabled"] is False
    assert status["cloud_voice"] == "off"
    assert status["silent_browser_fallback_allowed"] is False

    kokoro = synthesize_text("Hello AION")
    assert kokoro.provider == "kokoro"
    assert kokoro.fallback == "none"
    assert kokoro.reason in {"ok", "local_tts_error"}

    eleven = synthesize_text("Hello AION", provider="elevenlabs")
    assert eleven.ok is False
    assert eleven.provider == "elevenlabs"
    assert eleven.reason == "elevenlabs_disabled"
    assert eleven.metadata["would_call_elevenlabs"] is False

    browser = synthesize_text("Hello AION", provider="browser_speech")
    assert browser.ok is False
    assert browser.provider == "browser_speech"
    assert browser.reason == "browser_speech_disabled"
    assert browser.metadata["silent_fallback_allowed"] is False
