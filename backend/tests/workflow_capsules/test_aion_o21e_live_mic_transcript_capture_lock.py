from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"


def read_app() -> str:
    return APP.read_text(encoding="utf-8")

def read_o21e_block() -> str:
    text = read_app()
    marker = "AION O21E"
    start = text.find(marker)
    assert start >= 0
    return text[start:]


def test_o21e_live_mic_state_and_endpoint_exist():
    text = read_app()
    assert "AION O21E" in text
    assert "AION_O21E_STT_ENDPOINT" in text
    assert '"/api/aion/voice/stt"' in text
    assert "getAionO21ELiveMicTranscriptState" in text
    assert "__aionO21ELiveMicTranscriptState" in text


def test_o21e_uses_browser_mic_and_media_recorder():
    text = read_app()
    assert "navigator.mediaDevices.getUserMedia" in text
    assert "new MediaRecorder" in text
    assert 'recorder.start(2500)' in text
    assert "recorder.ondataavailable" in text
    assert "stopAionO21ELiveMicTranscriptCapture" in text


def test_o21e_posts_audio_chunks_to_stt_endpoint():
    text = read_app()
    assert "postAionO21EAudioChunkToStt" in text
    assert "new FormData()" in text
    assert 'form.append("file", blob' in text
    assert "fetch(AION_O21E_STT_ENDPOINT" in text
    assert "await response.json()" in text


def test_o21e_appends_transcripts_to_existing_terminal():
    text = read_app()
    assert "appendAionO21ETranscript" in text
    assert "getAionO21ETranscriptContainer" in text
    assert "data-aion-startup-transcript-log" in text
    assert "data-aion-o20c-conversation-transcript" in text
    assert "data-aion-o21e-live-transcript-row" in text


def test_o21e_visible_panel_is_mounted_without_new_overlay():
    text = read_app()
    assert "renderAionO21ELiveMicTranscriptPanel" in text
    assert "mountAionO21ELiveMicTranscriptPanel" in text
    assert "data-aion-o21e-live-mic-panel" in text
    assert "no_overlay_created: true" in text
    assert "document.body.appendChild(wrapper)" not in text


def test_o21e_business_twin_mutation_is_deferred():
    text = read_app()
    assert "business_twin_mutation_enabled: false" in text
    assert "Business Twin mutation: off" in text
    assert "does not mutate Business Twin fields yet" in text


def test_o21e_no_paid_voice_or_robotic_fallback():
    text = read_o21e_block()
    assert "no_elevenlabs_call: true" in text
    assert "no_browser_speech_fallback: true" in text
    assert "No hidden paid voice usage." in text
    assert "speechSynthesis.speak" not in text


def test_o21e_debug_exports_exist():
    text = read_app()
    assert "window.startAionO21ELiveMicTranscriptCapture" in text
    assert "window.stopAionO21ELiveMicTranscriptCapture" in text
    assert "window.toggleAionO21ELiveMicTranscriptCapture" in text
    assert "window.__debugAionO21ELiveMicTranscript" in text
