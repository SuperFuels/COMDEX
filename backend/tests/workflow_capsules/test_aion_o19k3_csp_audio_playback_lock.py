from pathlib import Path

APP = Path("desktop/mac/src/app.js")
HTML_CANDIDATES = [
    Path("desktop/mac/src/index.html"),
    Path("desktop/mac/index.html"),
    Path("desktop/mac/public/index.html"),
]

VOICE_ID = "onwK4e9ZLuTAKqWW03F9"


def test_o19k3_frontend_debug_lock_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O19K3 CSP AUDIO PLAYBACK LOCK" in text
    assert "__debugAionO19K3CspAudioPlayback" in text
    assert "audio_playback_failed_or_csp_blocked" in text
    assert 'const endpoints = [bridge.endpoint, bridge.fallback_endpoint];' in text
    assert 'file_endpoint: "/api/aion/voice/tts"' not in text


def test_o19k3_csp_allows_audio_blob_media():
    existing = [p for p in HTML_CANDIDATES if p.exists()]
    assert existing
    combined = "\n".join(p.read_text(encoding="utf-8") for p in existing)
    assert "Content-Security-Policy" in combined
    assert "media-src" in combined
    assert "blob:" in combined
    assert "data:" in combined
    assert "http://127.0.0.1:8080" in combined
    assert "http://localhost:8080" in combined


def test_o19k3_voice_id_still_working_voice():
    app_text = APP.read_text(encoding="utf-8")
    assert VOICE_ID in app_text
