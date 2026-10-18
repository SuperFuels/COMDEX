from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"


def read_app() -> str:
    return APP.read_text(encoding="utf-8")

def read_o21c_block() -> str:
    text = read_app()
    start = text.find("AION O21C")
    assert start >= 0
    next_markers = [
        text.find("AION O21D", start + 1),
        text.find("AION O21E", start + 1),
        text.find("AION O21F", start + 1),
    ]
    ends = [idx for idx in next_markers if idx >= 0]
    end = min(ends) if ends else len(text)
    return text[start:end]


def test_o21c_frontend_status_helpers_exist():
    text = read_app()
    assert "AION_O21C_VOICE_PROVIDER_STATUS_VERSION" in text
    assert "getAionVoiceProviderRuntimeStatusO21C" in text
    assert "renderAionVoiceProviderStatusPanelO21C" in text
    assert "syncAionVoiceProviderStatusPanelO21C" in text
    assert "installAionO21CVoiceProviderStatusSync" in text


def test_o21c_debug_helper_exposes_expected_provider_shape():
    text = read_app()
    assert "__debugAionVoiceProviders" in text
    assert 'tts_provider: isKokoro ? "kokoro"' in text
    assert 'stt_provider: isWhisper ? "faster_whisper"' in text
    assert "elevenlabs_enabled" in text
    assert "browser_fallback_enabled" in text
    assert "local_voice_ready" in text
    assert "cloud_voice_off" in text
    assert "no_elevenlabs_credits_required" in text


def test_o21c_terminal_renders_local_voice_labels():
    text = read_app()
    assert "Voice: ${escapeHtml(voiceStatus.tts_label)}" in text
    assert "STT: ${escapeHtml(voiceStatus.stt_label)}" in text
    assert "Cloud voice: ${escapeHtml(cloudLabel)}" in text
    assert "Using local voice. No ElevenLabs credits required." in text
    assert "Local Kokoro" in text
    assert "Local Whisper" in text


def test_o21c_does_not_create_another_overlay():
    text = read_o21c_block()
    assert "created_overlay: false" in text
    assert "document.createElement(\"div\")" not in text
    assert "insertAdjacentHTML(\"afterbegin\", html)" in text
    assert "[data-aion-o20c-conversation-terminal='true']" in text
    assert "[data-aion-business-entry-mode='true']" in text


def test_o21c_no_silent_robotic_browser_fallback():
    text = read_app()
    assert "no_silent_browser_fallback" in text
    assert "manual_browser_fallback_enabled" in text
    assert "browserFallbackEnabled ? \"manual_browser_fallback_enabled\" : \"no_silent_browser_fallback\"" in text
    assert "no_hidden_paid_usage" in text


def test_o21c_runtime_css_is_scoped_to_voice_status_panel():
    text = read_app()
    assert "installAionO21CVoiceProviderStatusStyles" in text
    assert "aion-o21c-voice-provider-status-style" in text
    assert ".aion-o21c-voice-provider-status" in text
    assert ".aion-o21c-voice-status-pill" in text


def test_o21c_preserves_existing_startup_renderer_names():
    text = read_app()
    assert "renderBusinessEntryModeSelector" in text
    assert "resetAionO20CConversation" in text
    assert "resetAionO20DVoiceAuthority" in text
    assert "__debugAionO20DSingleVoiceAuthority" in text
