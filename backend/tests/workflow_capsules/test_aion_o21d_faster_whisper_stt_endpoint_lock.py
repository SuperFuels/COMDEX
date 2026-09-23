from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
API = ROOT / "backend/modules/aion_voice/api.py"
PROVIDER = ROOT / "backend/modules/aion_voice/providers/faster_whisper_stt.py"
MAIN = ROOT / "backend/main.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_o21d_stt_provider_module_exists():
    text = read(PROVIDER)
    assert "AION_FAST_WHISPER_STT_VERSION" in text
    assert "SttResult" in text
    assert "get_faster_whisper_config" in text
    assert "transcribe_audio_bytes" in text
    assert "faster_whisper" in text


def test_o21d_stt_config_defaults_are_local_first():
    text = read(PROVIDER)
    assert 'os.getenv("AION_WHISPER_MODEL", "base")' in text
    assert 'os.getenv("AION_WHISPER_DEVICE", "auto")' in text
    assert 'os.getenv("AION_WHISPER_COMPUTE_TYPE", "int8")' in text
    assert 'provider="faster_whisper"' in text
    assert "local: bool = True" in text


def test_o21d_missing_dependency_fails_cleanly():
    text = read(PROVIDER)
    assert "local_stt_dependency_missing" in text
    assert "faster-whisper is not installed yet" in text
    assert "backend/requirements-voice-local.txt" in text
    assert "empty_audio" in text


def test_o21d_api_route_accepts_upload_file():
    text = read(API)
    assert "UploadFile" in text
    assert "File" in text
    assert '"/api/aion/voice/stt"' in text
    assert "async def aion_voice_stt" in text
    assert "await file.read()" in text
    assert "transcribe_audio_bytes" in text


def test_o21d_main_duplicate_route_guard_knows_stt_path():
    text = read(MAIN)
    assert "AION_VOICE_PROVIDER_ROUTE_PATHS" in text
    assert '"/api/aion/voice/stt"' in text
    assert "app.include_router(aion_voice_router)" in text


def test_o21d_response_contract_contains_required_fields():
    text = read(PROVIDER)
    assert "ok: bool" in text
    assert "provider: str" in text
    assert "text: str" in text
    assert "language: str | None" in text
    assert "segments: list[dict[str, Any]]" in text
    assert "reason: str | None" in text
    assert "message: str | None" in text


def test_o21d_no_cloud_stt_or_elevenlabs_fallback():
    text = read(PROVIDER)
    assert "elevenlabs" not in text.lower()
    assert "cloud_stt" not in text.lower()
    assert "browser_speech" not in text.lower()
