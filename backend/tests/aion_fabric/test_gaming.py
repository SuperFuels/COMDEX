from __future__ import annotations

import pytest

from backend.modules.aion_fabric.gaming import GovernedGamingExperience


def test_provider_open_search_and_playing_are_separate_evidence_states(tmp_path):
    games = GovernedGamingExperience(tmp_path)
    session = games.prepare_provider_handoff(query="Fortnite")
    assert session["state"] == "provider_surface_prepared"
    assert session["playing_verified"] is False

    opened = games.record_provider_observation(session["session_id"], observation="surface_open", evidence_source="webOS foreground browser")
    assert opened["provider_surface_open"] is True
    assert opened["playing_verified"] is False
    games.record_provider_observation(session["session_id"], observation="search_results", evidence_source="owner screen observation")
    selected = games.record_provider_observation(session["session_id"], observation="title_selected", evidence_source="provider page title", title="Fortnite")
    assert selected["title_verified"] is True
    with pytest.raises(PermissionError):
        games.record_provider_observation(session["session_id"], observation="playing", evidence_source="unsigned browser guess")
    games.record_provider_observation(session["session_id"], observation="stream_ready", evidence_source="provider readiness telemetry")
    playing = games.record_provider_observation(session["session_id"], observation="playing", evidence_source="signed provider telemetry", signed=True)
    assert playing["playing_verified"] is True


def test_controller_capability_is_not_compatibility_until_input_is_seen(tmp_path):
    games = GovernedGamingExperience(tmp_path)
    advertised = games.observe_controller(controller_id="phone-pad", capabilities=["buttons"], name="LG Mobile Gamepad")
    assert advertised["profile"] == "lg_mobile_gamepad"
    assert advertised["compatibility"] == "advertised_not_field_verified"
    assert advertised["gameplay_ready"] is False
    verified = games.observe_controller(controller_id="phone-pad", capabilities=["buttons"], input_events_seen=["button_a"])
    assert verified["compatibility"] == "verified"
    assert verified["gameplay_ready"] is True


def test_shortcuts_require_verified_title_and_remain_persona_private(tmp_path):
    games = GovernedGamingExperience(tmp_path)
    session = games.prepare_provider_handoff(query="Rocket League")
    with pytest.raises(PermissionError):
        games.save_shortcut(session["session_id"], persona_id="person_a")
    games.record_provider_observation(session["session_id"], observation="title_selected", evidence_source="provider title", title="Rocket League")
    games.save_shortcut(session["session_id"], persona_id="person_a")
    assert len(games.snapshot(persona_id="person_a")["shortcuts"]) == 1
    assert games.snapshot(persona_id="person_b")["shortcuts"] == []
    continuation = games.continue_last(persona_id="person_a")
    assert continuation["continuation"] == "prepared_not_playing"
    assert continuation["query"] == "Rocket League"


def test_mobile_game_sessions_do_not_leak_between_private_identities(tmp_path):
    games = GovernedGamingExperience(tmp_path)
    games.prepare_provider_handoff(query="Fortnite", persona_id="person_a")
    assert games.snapshot(persona_id="person_a")["latest_session"]["query"] == "Fortnite"
    assert games.snapshot(persona_id="person_b")["latest_session"] is None
