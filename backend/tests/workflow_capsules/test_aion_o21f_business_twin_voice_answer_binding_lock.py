from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def read_o21f_block() -> str:
    text = read_app()
    marker = "AION O21F"
    start = text.find(marker)
    assert start >= 0
    return text[start:]


def test_o21f_business_twin_voice_binding_block_exists():
    text = read_o21f_block()
    assert "AION_O21F_BUSINESS_TWIN_VOICE_BINDING_VERSION" in text
    assert "getAionO21FBusinessTwinVoiceAnswerState" in text
    assert "bindAionO21FTranscriptToBusinessTwinAnswer" in text
    assert "mountAionO21FBusinessTwinVoiceBinding" in text


def test_o21f_uses_correct_startup_route_and_blocks_business_context_hijack():
    text = read_o21f_block()
    assert 'const AION_O21F_STARTUP_ROUTE = "small_business_foundation"' in text
    assert "business_context_hijack_allowed: false" in text
    assert "no business_context hijack" in text
    assert "business_context" in text


def test_o21f_keeps_human_approval_and_no_external_actions():
    text = read_o21f_block()
    assert "approval_required: true" in text
    assert "external_actions_allowed: false" in text
    assert "No external actions" in text
    assert "human approval required" in text
    assert "book" in text
    assert "pay" in text
    assert "send" in text
    assert "publish" in text


def test_o21f_classifies_core_business_twin_fields():
    text = read_o21f_block()
    assert "business_name" in text
    assert "services" in text
    assert "location" in text
    assert "target_customers" in text
    assert "current_goal" in text
    assert "idea_mode_answer" in text
    assert "general_business_context" in text


def test_o21f_patches_o21e_transcript_append_without_replacing_terminal():
    text = read_o21f_block()
    assert "patchAionO21ETranscriptBindingForBusinessTwin" in text
    assert "const originalAppend = window.appendAionO21ETranscript" in text
    assert "window.appendAionO21ETranscript = function appendAionO21ETranscriptWithBusinessTwinBinding" in text
    assert "bindAionO21FTranscriptToBusinessTwinAnswer" in text


def test_o21f_renders_visible_pending_review_panel():
    text = read_o21f_block()
    assert "renderAionO21FBusinessTwinVoiceBindingPanel" in text
    assert "data-aion-o21f-business-twin-voice-binding" in text
    assert "Pending review" in text
    assert "Business Twin voice answers" in text


def test_o21f_debug_exports_exist():
    text = read_o21f_block()
    assert "window.getAionO21FBusinessTwinVoiceAnswerState" in text
    assert "window.classifyAionO21FVoiceAnswerField" in text
    assert "window.bindAionO21FTranscriptToBusinessTwinAnswer" in text
    assert "window.__debugAionO21FBusinessTwinVoiceAnswers" in text


def test_o21f_does_not_call_paid_voice_or_browser_speech():
    text = read_o21f_block()
    assert "ElevenLabs" not in text
    assert "speechSynthesis.speak" not in text
    assert "fetch(" not in text
