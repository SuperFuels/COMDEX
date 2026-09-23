from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.modules.aion_fabric.entertainment_personalization import PrivateEntertainmentPersonalization


def test_private_and_shared_watchlists_do_not_leak_between_personas(tmp_path):
    service = PrivateEntertainmentPersonalization(tmp_path)
    service.add_watchlist(persona_id="kevin", title="Private Film", visibility="private")
    service.add_watchlist(persona_id="kevin", title="Family Film", visibility="household_shared")

    mia = service.snapshot(persona_id="mia")
    assert [item["title"] for item in mia["watchlists"]] == ["Family Film"]
    assert mia["private_history"] == []


def test_contextual_recommendation_uses_only_owner_or_explicitly_shared_history(tmp_path):
    service = PrivateEntertainmentPersonalization(tmp_path)
    service.remember(persona_id="kevin", title="Hidden Favourite", outcome="liked", share_with_household=False)
    service.remember(persona_id="mia", title="Already Watched", outcome="watched", share_with_household=True)
    candidates = [
        {"title": "Already Watched", "minutes": 90, "moods": ["funny"], "family_safe": True},
        {"title": "New Comedy", "minutes": 88, "moods": ["funny"], "family_safe": True},
    ]

    result = service.recommend(persona_id="kevin", candidates=candidates, mood="funny", maximum_minutes=100, presence="family", hour=21)
    shared = service.recommend(persona_id=None, candidates=candidates, mood="funny", maximum_minutes=100, presence="family", hour=21)

    assert [item["title"] for item in result["items"]] == ["New Comedy"]
    assert [item["title"] for item in shared["items"]] == ["New Comedy"]
    assert result["unconsented_other_person_history_used"] is False
    assert all(item["entitlement"] == "unknown_until_authenticated_provider_confirms" for item in result["items"])


def test_episode_reminder_requires_exact_provider_metadata_and_stays_local(tmp_path):
    service = PrivateEntertainmentPersonalization(tmp_path)
    with pytest.raises(ValueError):
        service.add_episode_reminder(persona_id="owner", programme={"episode_title": "Episode 2"}, notify_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat())
    reminder = service.add_episode_reminder(
        persona_id="owner",
        programme={"provider": "Netflix", "provider_content_id": "12345", "series_title": "Series", "episode_title": "Episode 2"},
        notify_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    )

    assert reminder["status"] == "scheduled_local_private_inbox"
    assert reminder["external_push_scheduled"] is False


def test_provider_health_guides_official_sign_in_without_credentials(tmp_path):
    health = PrivateEntertainmentPersonalization(tmp_path).record_service_health(
        provider="Netflix", status="sign_in_required", source="signed_native_adapter", authenticated=True
    )

    assert "official provider sign-in" in health["recovery"]
    assert health["credentials_inspected"] is False


def test_shared_tv_history_waits_for_private_claim(tmp_path):
    service = PrivateEntertainmentPersonalization(tmp_path)
    pending = service.prepare_history(title="The Crown", outcome="liked")

    assert pending["status"] == "awaiting_private_claim"
    assert service.snapshot(persona_id="mia")["private_history"] == []
    claimed = service.claim_history(pending["pending_id"], persona_id="kevin")
    assert claimed["persona_id"] == "kevin"
    assert service.snapshot(persona_id="mia")["private_history"] == []
