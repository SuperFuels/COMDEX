from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
LAUNCHER = ROOT / "desktop/mac/electron/main.js"


def read_launcher() -> str:
    return LAUNCHER.read_text(encoding="utf-8", errors="ignore")


def test_o25n_desktop_backend_local_voice_env_lock_exists():
    text = read_launcher()
    assert "AION O25N desktop backend local voice env lock" in text
    assert "aionO25NLocalVoiceBackendEnv" in text
    assert "AION_VOICE_WORKER_ENABLED" in text
    assert "AION_TTS_PROVIDER" in text
    assert "kokoro" in text
    assert "AION_LOCAL_VOICE_ENABLED" in text
    assert "AION_ELEVENLABS_ENABLED" in text
    assert "AION_VOICE_NO_HIDDEN_DOWNLOADS" in text
    assert "AION_VOICE_RUNTIME_MODE" in text


def test_o25n_desktop_backend_launcher_uses_local_voice_env():
    text = read_launcher()
    assert "backend.main:app" in text or "uvicorn" in text
    assert "env: aionO25NLocalVoiceBackendEnv()" in text
    assert "env: process.env" not in text
    assert "env: { ...process.env }" not in text


def test_o25n_js_syntax():
    subprocess.run(["node", "--check", str(LAUNCHER)], cwd=ROOT, check=True)
