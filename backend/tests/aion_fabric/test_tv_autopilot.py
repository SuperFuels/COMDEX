from __future__ import annotations

from backend.modules.aion_fabric.autopilot import TVAutopilot
from backend.modules.aion_fabric.voice import VoiceControlService, parse_voice_intent


def test_autopilot_persists_belief_and_explainable_plan(tmp_path):
    autopilot = TVAutopilot(tmp_path)
    plan_id = autopilot.start_plan(
        name="Movie Mode",
        goal="Open Netflix safely",
        steps=[{"name": "Open Netflix"}, {"name": "Set volume", "verification": "read-after-write"}],
    )
    autopilot.mark_step(plan_id, 0, status="verified", evidence="receipt_one")
    autopilot.mark_step(plan_id, 1, status="verified", evidence="receipt_two")
    autopilot.finish_plan(plan_id, status="completed", summary="All steps verified")
    autopilot.observe(surface="netflix", confidence=0.76, evidence="launch acknowledged")

    restored = TVAutopilot(tmp_path).snapshot()
    assert restored["belief"]["surface"] == "netflix"
    assert restored["belief"]["pixel_vision"] is False
    assert restored["last_plan"]["status"] == "completed"
    assert all(step["status"] == "verified" for step in restored["last_plan"]["steps"])


def test_owner_cancel_stops_active_autopilot_steps(tmp_path):
    autopilot = TVAutopilot(tmp_path)
    autopilot.start_plan(
        name="Open service",
        goal="Navigate to a title",
        steps=[{"name": "Open app"}, {"name": "Choose title"}],
    )

    cancelled = autopilot.cancel_active(summary="Voice cancellation")

    assert cancelled["status"] == "cancelled"
    assert all(step["status"] == "skipped" for step in cancelled["steps"])
    assert autopilot.snapshot()["active_plan"] is None


def test_voice_follow_up_resolves_profile_without_repeating_wake_phrase():
    service = VoiceControlService(lambda transcript: {"spoken_response": transcript})
    service._follow_up = {"kind": "netflix_profile"}
    service._follow_up_until = float("inf")
    resolved = service._resolve_follow_up("the second one")
    assert resolved == "Pilot select the second Netflix profile"
    intent = parse_voice_intent(resolved)
    assert intent is not None
    assert intent.action == "netflix_profile"
    assert intent.arguments["profile_index"] == 2

    service._follow_up = {"kind": "research_result"}
    service._follow_up_until = float("inf")
    resolved = service._resolve_follow_up("open the third one")
    assert resolved == "Pilot open the third result"

    service._follow_up = {"kind": "agent_refinement"}
    service._follow_up_until = float("inf")
    resolved = service._resolve_follow_up("mid-range, travelling by car")
    assert resolved == "Pilot update the plan with mid range travelling by car"


def test_autopilot_remembers_verified_and_failed_navigation_paths(tmp_path):
    autopilot = TVAutopilot(tmp_path)
    autopilot.record_navigation_attempt(
        action="launch_app",
        expected="netflix",
        observed="foreground=netflix",
        success=True,
    )
    autopilot.record_navigation_attempt(
        action="netflix_profile",
        expected="profile 2",
        observed="transport verified; screen not observed",
        success=False,
    )
    memory = autopilot.snapshot()["navigation_memory"]
    assert memory["launch_app"]["successes"] == 1
    assert memory["netflix_profile"]["failures"] == 1


def test_voice_sleep_closes_capture_state_until_explicit_resume():
    service = VoiceControlService(lambda transcript: {"spoken_response": "ok"})
    service.sleep()
    status = service.status()
    assert status["sleeping"] is True
    assert status["ready"] is False
    assert status["microphone"] == "closed"
    assert status["privacy"] == "microphone_closed_no_audio_capture"
    assert status["activity_state"] == "sleeping"
    assert status["activity_history"][-1]["contains_audio"] is False
    assert status["activity_history"][-1]["contains_transcript"] is False


def test_voice_preferences_are_local_bounded_and_support_quiet_mode(tmp_path):
    settings = tmp_path / "voice.json"
    service = VoiceControlService(lambda transcript: {"spoken_response": "ok"}, settings_path=settings)
    status = service.set_preferences(voice_name="Samantha", speech_rate=999, quiet_mode=True)
    assert status["voice_name"] == "Samantha"
    assert status["speech_rate"] == 240
    assert status["quiet_mode"] is True
    restored = VoiceControlService(lambda transcript: {"spoken_response": "ok"}, settings_path=settings).status()
    assert restored["voice_name"] == "Samantha"
    assert restored["speech_rate"] == 240
    assert restored["quiet_mode"] is True

    try:
        service.set_preferences(voice_name="Remote cloud voice")
    except ValueError as exc:
        assert "Unsupported" in str(exc)
    else:
        raise AssertionError("An unapproved voice must fail closed")


def test_voice_quiet_hours_support_overnight_schedule_and_persist(tmp_path):
    settings = tmp_path / "voice.json"
    service = VoiceControlService(lambda transcript: {"spoken_response": "ok"}, settings_path=settings)
    result = service.set_preferences(quiet_start="21:30", quiet_end="07:15")
    assert result["quiet_schedule_active"] is True
    assert VoiceControlService._within_quiet_schedule("21:30", "07:15", now_minutes=23 * 60) is True
    assert VoiceControlService._within_quiet_schedule("21:30", "07:15", now_minutes=12 * 60) is False
    restored = VoiceControlService(lambda transcript: {"spoken_response": "ok"}, settings_path=settings).status()
    assert restored["quiet_start"] == "21:30"
    assert restored["quiet_end"] == "07:15"


def test_voice_quiet_hours_reject_invalid_clock_values(tmp_path):
    service = VoiceControlService(lambda transcript: {"spoken_response": "ok"}, settings_path=tmp_path / "voice.json")
    try:
        service.set_preferences(quiet_start="25:00", quiet_end="07:00")
    except ValueError as exc:
        assert "HH:MM" in str(exc)
    else:
        raise AssertionError("Invalid quiet-hour time must fail closed")


def test_private_push_to_talk_transcribes_locally_and_deletes_audio(tmp_path, monkeypatch):
    seen = {}

    class Segment:
        text = "open Netflix"

    class Model:
        def transcribe(self, path, **kwargs):
            seen["path"] = path
            seen["existed_during_transcription"] = __import__("os").path.exists(path)
            return [Segment()], None

    service = VoiceControlService(lambda transcript: {"spoken_response": "ok"})
    monkeypatch.setattr(service, "_load_model", lambda: Model())
    transcript = service.transcribe_push_to_talk(b"bounded-private-audio", "audio/mp4")

    assert transcript == "open Netflix"
    assert seen["existed_during_transcription"] is True
    assert __import__("os").path.exists(seen["path"]) is False
    assert service.status()["phone_push_to_talk_count"] == 1
