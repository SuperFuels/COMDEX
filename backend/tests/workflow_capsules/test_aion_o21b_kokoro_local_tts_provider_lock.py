from __future__ import annotations

import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_o21b_kokoro_provider_has_real_local_generation_path():
    text = read("backend/modules/aion_voice/providers/kokoro_tts.py")
    assert "from kokoro import KPipeline" in text
    assert "import soundfile as sf" in text
    assert "sf.write" in text
    assert "audio/wav" in text
    assert "x-aion-voice-local" in text
    assert "x-aion-voice-cache" in text
    assert ".runtime/voice_cache" in text
    assert "AION_KOKORO_VOICE" in text
    assert "AION_KOKORO_SAMPLE_RATE" in text


def test_o21b_kokoro_dependencies_are_optional_not_imported_at_module_load():
    text = read("backend/modules/aion_voice/providers/kokoro_tts.py")
    before_function_body = text.split("def _load_pipeline", 1)[0]
    assert "from kokoro import KPipeline" not in before_function_body
    assert "import soundfile as sf" not in before_function_body


def test_o21b_requirements_file_documents_local_voice_deps():
    text = read("backend/requirements-voice-local.txt")
    assert "kokoro" in text
    assert "soundfile" in text


def test_o21b_kokoro_generates_wav_with_fake_runtime(monkeypatch, tmp_path):
    from backend.modules.aion_voice.providers import kokoro_tts

    kokoro_tts.reset_kokoro_provider_for_tests()

    class FakePipeline:
        def __init__(self, lang_code: str = "a"):
            self.lang_code = lang_code

        def __call__(self, text: str, voice: str = "af_heart"):
            yield (None, None, [0.0, 0.1, -0.1, 0.0])

    fake_kokoro = types.ModuleType("kokoro")
    fake_kokoro.KPipeline = FakePipeline

    fake_soundfile = types.ModuleType("soundfile")

    def fake_write(path: str, audio, sample_rate: int, format: str = "WAV"):
        Path(path).write_bytes(b"RIFF_FAKE_KOKORO_WAV")

    fake_soundfile.write = fake_write

    monkeypatch.setitem(sys.modules, "kokoro", fake_kokoro)
    monkeypatch.setitem(sys.modules, "soundfile", fake_soundfile)
    monkeypatch.setenv("AION_VOICE_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("AION_KOKORO_VOICE", "af_heart")
    monkeypatch.setenv("AION_KOKORO_SAMPLE_RATE", "24000")

    first = kokoro_tts.synthesize_with_kokoro("Hello from local AION voice.")
    assert first.ok is True
    assert first.provider == "kokoro"
    assert first.media_type == "audio/wav"
    assert first.audio_bytes == b"RIFF_FAKE_KOKORO_WAV"
    assert first.headers["x-aion-voice-provider"] == "kokoro"
    assert first.headers["x-aion-voice-local"] == "true"
    assert first.headers["x-aion-voice-cache"] == "miss"
    assert first.metadata["cache_hit"] is False
    assert Path(first.metadata["cache_path"]).exists()

    second = kokoro_tts.synthesize_with_kokoro("Hello from local AION voice.")
    assert second.ok is True
    assert second.audio_bytes == b"RIFF_FAKE_KOKORO_WAV"
    assert second.headers["x-aion-voice-cache"] == "hit"
    assert second.metadata["cache_hit"] is True


def test_o21b_router_uses_kokoro_without_elevenlabs(monkeypatch, tmp_path):
    from backend.modules.aion_voice.providers import kokoro_tts
    from backend.modules.aion_voice.voice_router import synthesize_text

    kokoro_tts.reset_kokoro_provider_for_tests()

    class FakePipeline:
        def __init__(self, lang_code: str = "a"):
            pass

        def __call__(self, text: str, voice: str = "af_heart"):
            yield (None, None, [0.0, 0.0])

    fake_kokoro = types.ModuleType("kokoro")
    fake_kokoro.KPipeline = FakePipeline

    fake_soundfile = types.ModuleType("soundfile")
    fake_soundfile.write = lambda path, audio, sample_rate, format="WAV": Path(path).write_bytes(b"RIFF_ROUTER_WAV")

    monkeypatch.setitem(sys.modules, "kokoro", fake_kokoro)
    monkeypatch.setitem(sys.modules, "soundfile", fake_soundfile)
    monkeypatch.setenv("AION_VOICE_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("AION_TTS_PROVIDER", "kokoro")
    monkeypatch.setenv("AION_ALLOW_ELEVENLABS", "false")
    monkeypatch.setenv("AION_ALLOW_BROWSER_SPEECH", "false")

    result = synthesize_text("AION local voice route test.")
    assert result.ok is True
    assert result.provider == "kokoro"
    assert result.audio_bytes == b"RIFF_ROUTER_WAV"
    assert result.fallback == "none"
    assert result.headers["x-aion-voice-provider"] == "kokoro"


def test_o21b_elevenlabs_still_blocked_unless_enabled(monkeypatch):
    from backend.modules.aion_voice.voice_router import synthesize_text

    monkeypatch.setenv("AION_TTS_PROVIDER", "kokoro")
    monkeypatch.setenv("AION_ALLOW_ELEVENLABS", "false")

    result = synthesize_text("Do not spend credits.", provider="elevenlabs")
    assert result.ok is False
    assert result.provider == "elevenlabs"
    assert result.reason == "elevenlabs_disabled"
    assert result.fallback == "none"
    assert result.metadata["would_call_elevenlabs"] is False


def test_o21b_main_forces_voice_router_to_win_duplicate_route_conflict():
    text = read("backend/main.py")
    assert "AION_VOICE_PROVIDER_ROUTE_PATHS" in text
    assert '"/api/aion/voice/tts"' in text
    assert '"/api/aion/voice/providers"' in text
    assert "app.include_router(aion_voice_router)" in text
