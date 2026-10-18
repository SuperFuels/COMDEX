from pathlib import Path

APP = Path("desktop/mac/src/app.js")
MAIN = Path("backend/main.py")
ENV = Path("backend/.env.local")

VOICE_ID = "onwK4e9ZLuTAKqWW03F9"


def test_o19k_backend_route_installed():
    text = MAIN.read_text(encoding="utf-8")
    assert "BEGIN AION O19K ELEVENLABS VOICE BRIDGE LOCK" in text
    assert '@app.post("/api/aion/voice/tts")' in text
    assert "ELEVENLABS_API_KEY" in text
    assert "AION_ELEVENLABS_VOICE_ID" in text
    assert VOICE_ID in text
    assert "audio/mpeg" in text
    assert "xi-api-key" in text


def test_o19k_frontend_bridge_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O19K ELEVENLABS FRONTEND VOICE BRIDGE LOCK" in text
    assert "__debugAionO19KElevenLabsVoiceBridge" in text
    assert "/api/aion/voice/tts" in text
    assert VOICE_ID in text
    assert "browser_speech_fallback" in text
    assert "new Audio(audioUrl)" in text


def test_o19k_speak_function_uses_elevenlabs_first():
    text = APP.read_text(encoding="utf-8")
    start = text.index("async function speakO19I")
    block = text[start:start + 9000]
    assert "provider: \"elevenlabs\"" in block
    assert "fetch(endpoint" in block
    assert "response.blob()" in block
    assert "audio.play()" in block
    assert "browser_speech_fallback" in block


def test_o19k_env_voice_id_written_without_api_key():
    text = ENV.read_text(encoding="utf-8")
    assert f"AION_ELEVENLABS_VOICE_ID={VOICE_ID}" in text
    assert f"ELEVENLABS_VOICE_ID={VOICE_ID}" in text
    assert "ELEVENLABS_MODEL_ID=eleven_multilingual_v2" in text
    assert "ELEVENLABS_API_KEY=" not in text
