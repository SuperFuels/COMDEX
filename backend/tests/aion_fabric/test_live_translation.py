from __future__ import annotations

from backend.modules.aion_fabric.live_translation import LocalLiveTranslation
from backend.modules.aion_fabric.voice import parse_voice_intent


def test_live_translation_uses_offline_phrasebook_and_preserves_playback(tmp_path, monkeypatch):
    monkeypatch.setenv("AION_LOCAL_LLM_ENABLED", "0")
    service = LocalLiveTranslation(tmp_path)
    result = service.translate(
        live_context={"context_hash": "a" * 64, "recent_transcripts": ["Buenos días"]},
        screen_understanding=None,
        target_language="english",
    )

    assert result["translation"] == "Good morning."
    assert result["provider"] == "aion_local_phrasebook"
    assert result["internet_used"] is False
    assert result["paid_ai_used"] is False
    assert result["raw_audio_retained"] is False
    assert result["presentation"]["playback_preserved"] is True
    assert service.latest()["translation_id"] == result["translation_id"]


def test_live_translation_prefers_captured_subtitle_when_requested(tmp_path, monkeypatch):
    monkeypatch.setenv("AION_LOCAL_LLM_ENABLED", "0")
    result = LocalLiveTranslation(tmp_path).translate(
        live_context={"context_hash": "b" * 64, "recent_transcripts": ["unrelated dialogue"]},
        screen_understanding={"subtitles": {"lines": ["Thank you"]}},
        target_language="spanish",
        source_kind="subtitle",
    )

    assert result["source_text"] == "Thank you"
    assert result["source_evidence"] == "owner_captured_subtitle"
    assert result["translation"] == "Gracias."
    assert result["target_language"] == "es"


def test_live_translation_is_honest_when_no_local_route_can_translate(tmp_path, monkeypatch):
    monkeypatch.setenv("AION_LOCAL_LLM_ENABLED", "0")
    result = LocalLiveTranslation(tmp_path).translate(
        live_context={"context_hash": "c" * 64, "recent_transcripts": ["A complex unfamiliar sentence"]},
        screen_understanding=None,
        target_language="english",
    )

    assert result["translation"] == ""
    assert result["confidence"] == 0
    assert result["provider"] == "honest_limitation"


def test_translation_voice_intents_include_target_and_source():
    assert parse_voice_intent("Pilot translate that into Spanish").to_dict()["arguments"] == {
        "target_language": "spanish", "source_kind": "dialogue"
    }
    assert parse_voice_intent("Pilot translate that subtitle to English").to_dict()["arguments"] == {
        "target_language": "english", "source_kind": "subtitle"
    }
