from __future__ import annotations

import pytest

from backend.modules.aion_fabric.live_engagement import HouseholdLiveEngagement
from backend.modules.aion_fabric.voice import parse_voice_intent


def _event(home_score=2, away_score=0):
    return {
        "provider": {"authenticated": True},
        "authenticated_provider_fact": {
            "provider_match_id": "42",
            "home": "Real Madrid",
            "away": "Barcelona",
            "competition": "Example League",
            "home_score": home_score,
            "away_score": away_score,
            "last_updated": f"update-{home_score}-{away_score}",
        },
    }


def test_close_watch_requires_private_claim_and_notifies_once_on_threshold_transition(tmp_path):
    service = HouseholdLiveEngagement(tmp_path)
    watch = service.prepare_close_watch(live_event=_event(), margin=1)

    assert watch["status"] == "awaiting_private_claim"
    assert service.evaluate(_event(2, 1)) == []
    claimed = service.claim_watch(watch["watch_id"], persona_id="persona_owner")
    first = service.evaluate(_event(2, 1))
    second = service.evaluate(_event(2, 1))

    assert claimed["status"] == "active"
    assert first[0]["delivery"] == "private_phone_inbox"
    assert first[0]["external_push_sent"] is False
    assert second == []


def test_prediction_and_commentary_are_persona_bound_and_never_betting(tmp_path):
    service = HouseholdLiveEngagement(tmp_path)
    prediction = service.add_prediction(live_event=_event(), persona_id="persona_owner", prediction="Barcelona scores next")
    commentary = service.set_commentary(persona_id="persona_owner", style="child_friendly")

    assert prediction["money_or_betting_enabled"] is False
    assert commentary["audio_replaced"] is False
    assert service.snapshot(persona_id="another_person")["predictions"] == []


def test_live_engagement_requires_authenticated_match_and_routes_voice(tmp_path):
    service = HouseholdLiveEngagement(tmp_path)
    with pytest.raises(ValueError):
        service.prepare_close_watch(live_event={"provider": {"authenticated": False}}, margin=1)

    intent = parse_voice_intent("Pilot notify me when this match becomes close")
    explicit = parse_voice_intent("Pilot notify me when the game is within 2 goals")
    assert intent.action == "live_engagement"
    assert intent.arguments["margin"] == 1
    assert explicit.arguments["margin"] == 2
