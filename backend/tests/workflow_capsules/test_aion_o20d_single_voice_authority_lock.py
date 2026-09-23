from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_o20d_single_voice_authority_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O20D SINGLE VOICE AUTHORITY LOCK" in text
    assert "__debugAionO20DSingleVoiceAuthority" in text
    assert "resetAionO20DVoiceAuthority" in text
    assert "[AION] O20D single voice authority installed" in text


def test_o20d_wraps_tts_fetch_and_blocks_duplicates():
    text = APP.read_text(encoding="utf-8")
    block = text.split("BEGIN AION O20D SINGLE VOICE AUTHORITY LOCK", 1)[1].split("END AION O20D SINGLE VOICE AUTHORITY LOCK", 1)[0]
    assert "/api/aion/voice/tts" in block
    assert "duplicate_voice_request_blocked" in block
    assert "cooldown_ms: 0" in block
    assert "if (state.in_flight) return true" in block
    assert "now - state.last_real_tts_at" not in block
    assert "window.fetch = wrappedFetch" in block
    assert "__aionO20DAuthorityWrapped" in block


def test_o20d_blocks_browser_robotic_fallback_by_default():
    text = APP.read_text(encoding="utf-8")
    block = text.split("BEGIN AION O20D SINGLE VOICE AUTHORITY LOCK", 1)[1].split("END AION O20D SINGLE VOICE AUTHORITY LOCK", 1)[0]
    assert "browser_robotic_fallback_disabled" in block
    assert "window.__aionO20DAllowBrowserFallback !== true" in block
    assert "synth.speak = wrappedSpeak" in block
    assert "__aionO20DBrowserFallbackWrapped" in block


def test_o20d_renders_clear_quota_or_provider_error_banner():
    text = APP.read_text(encoding="utf-8")
    block = text.split("BEGIN AION O20D SINGLE VOICE AUTHORITY LOCK", 1)[1].split("END AION O20D SINGLE VOICE AUTHORITY LOCK", 1)[0]
    assert "ElevenLabs quota exhausted" in block
    assert "ElevenLabs voice unavailable" in block
    assert "Browser robotic fallback is disabled" in block
    assert "data-aion-o20d-voice-status" in block
