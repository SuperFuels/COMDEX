from __future__ import annotations

from backend.modules.aion_fabric.scene_explanation import SpoilerAwareSceneExplanation
from backend.modules.aion_fabric.voice import parse_voice_intent


def test_scene_explanation_uses_only_observed_evidence_and_preserves_playback(tmp_path, monkeypatch):
    monkeypatch.setenv("AION_LOCAL_LLM_ENABLED", "0")
    service = SpoilerAwareSceneExplanation(tmp_path)
    result = service.explain(
        live_context={
            "context_hash": "a" * 64,
            "recent_transcripts": ["She said the train leaves at midnight."],
            "playback": {"position": 1200, "duration": 3600},
        },
        screen_understanding={
            "summary": "Two people are talking beside a station clock.",
            "subtitles": {"lines": ["We only have ten minutes."]},
        },
        request_kind="recap",
    )

    assert result["spoiler_policy"] == "observed_evidence_only"
    assert result["future_plot_sources_used"] is False
    assert result["internet_plot_search_used"] is False
    assert result["presentation"]["playback_preserved"] is True
    assert result["playback_boundary"]["progress_percent"] == 33.3
    assert set(result["evidence_kinds"]) == {
        "local_recent_dialogue",
        "owner_captured_scene_summary",
        "owner_captured_subtitle",
    }
    assert service.latest()["explanation_id"] == result["explanation_id"]


def test_scene_explanation_refuses_to_guess_without_current_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("AION_LOCAL_LLM_ENABLED", "0")
    result = SpoilerAwareSceneExplanation(tmp_path).explain(
        live_context={"context_hash": "b" * 64, "playback": {}},
        screen_understanding=None,
        request_kind="scene",
    )

    assert result["confidence"] == 0
    assert result["provider"] == "honest_limitation"
    assert "risking a spoiler" in result["answer"]
    assert result["playback_boundary"]["known"] is False


def test_child_learning_mode_uses_only_observed_scene_and_builds_bounded_activity(tmp_path, monkeypatch):
    monkeypatch.setenv("AION_LOCAL_LLM_ENABLED", "0")
    result = SpoilerAwareSceneExplanation(tmp_path).explain(
        live_context={"context_hash": "c" * 64, "recent_transcripts": ["The apple falls from the tree."], "playback": {}},
        screen_understanding={"summary": "An apple falls beside a child."},
        request_kind="learning",
        audience="child",
        detail_level="simple",
        learning_subject="science",
    )

    assert result["audience"] == "child"
    assert result["detail_level"] == "simple"
    assert result["learning_subject"] == "science"
    assert result["learning_activity"]["subject"] == "science"
    assert "observed scene" in result["answer"]
    assert result["future_plot_sources_used"] is False
    assert result["presentation"]["playback_preserved"] is True


def test_accessibility_summary_does_not_identify_people(tmp_path, monkeypatch):
    monkeypatch.setenv("AION_LOCAL_LLM_ENABLED", "0")
    result = SpoilerAwareSceneExplanation(tmp_path).explain(
        live_context={"context_hash": "d" * 64, "playback": {}},
        screen_understanding={"summary": "Two people stand beside a red train."},
        request_kind="accessibility",
        detail_level="detailed",
    )

    assert result["accessibility_summary"] == "Two people stand beside a red train."
    assert result["request_kind"] == "accessibility"
    assert result["internet_plot_search_used"] is False


def test_contextual_scene_voice_modes_are_explicit():
    assert parse_voice_intent("Pilot, why is that funny?").arguments["kind"] == "joke"
    assert parse_voice_intent("Pilot, explain that reference").arguments["kind"] == "reference"
    assert parse_voice_intent("Pilot, explain this to a child").arguments == {
        "kind": "scene", "audience": "child", "detail_level": "simple"
    }
    assert parse_voice_intent("Pilot, describe this scene").arguments == {
        "kind": "accessibility", "detail_level": "detailed"
    }
    assert parse_voice_intent("Pilot, turn this scene into a science lesson").arguments == {
        "kind": "learning", "audience": "child", "detail_level": "simple", "learning_subject": "science"
    }
