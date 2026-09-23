from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_o22d_voice_worker_exists_and_is_generic():
    text = read("scripts/aion_voice_worker.py")
    assert "def run_tts" in text
    assert "def run_stt" in text
    assert "KPipeline" in text
    assert "WhisperModel" in text
    assert "business_context_hardcoded" in text
    forbidden = [
        "Home" + " Fixed",
        "Al" + "meria",
        "Al" + "mería",
        "Mur" + "cia",
        "Mo" + "jacar",
        "per" + "gola",
        "paint" + "ing",
        "construct" + "ion",
    ]
    for token in forbidden:
        assert token not in text


def test_o22d_bridge_uses_isolated_or_bundled_voice_python():
    text = read("backend/modules/aion_voice/voice_worker_bridge.py")
    assert "AION_VOICE_PYTHON" in text
    assert ".venv_voice" in text
    assert "Contents" in text
    assert "Resources" in text
    assert "voice" in text
    assert "subprocess.run" in text
    assert "aion_voice_worker.py" in text


def test_o22d_bridge_has_tts_and_stt_helpers():
    text = read("backend/modules/aion_voice/voice_worker_bridge.py")
    assert "def synthesize_with_worker" in text
    assert "def transcribe_with_worker" in text
    assert "audio_base64" in text
    assert "af_heart" in text
    assert "AION_WHISPER_MODEL" in text


def test_o22d_packaging_contract_mentions_no_hidden_downloads():
    requirements = read("backend/requirements-voice-runtime.txt")
    assert "kokoro" in requirements
    assert "faster-whisper" in requirements
    assert "soundfile" in requirements
    assert "python-multipart" in requirements
