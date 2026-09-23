from __future__ import annotations

import pytest

from backend.modules.aion_fabric.entertainment_execution import VerifiedEntertainmentExecution


def _receipt(*, verified=True, foreground="netflix"):
    return {
        "receipt_id": "receipt_1",
        "action": "netflix_search",
        "verified": verified,
        "after": {"foreground_app_id": foreground, "screen_effect_observed": bool(foreground)},
    }


@pytest.mark.parametrize(
    ("url", "provider"),
    [
        ("https://www.netflix.com/title/81234567", "Netflix"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "YouTube"),
        ("https://youtu.be/dQw4w9WgXcQ", "YouTube"),
        ("https://www.primevideo.com/detail/B0ABCDE12", "Prime Video"),
        ("https://www.disneyplus.com/movies/example/abc123", "Disney+"),
    ],
)
def test_exact_official_routes_are_classified(url, provider):
    route = VerifiedEntertainmentExecution.classify_official_route(url)
    assert route["provider"] == provider
    assert route["canonical_url"].startswith("https://")


@pytest.mark.parametrize(
    "url",
    [
        "http://www.netflix.com/title/81234567",
        "https://user:secret@netflix.com/title/81234567",
        "https://www.netflix.com/search?q=The+Crown",
        "https://www.justwatch.com/es/serie/the-crown",
        "https://evil.example/title/81234567",
        "https://www.youtube.com/results?search_query=The+Crown",
    ],
)
def test_catalogue_search_and_unsafe_routes_fail_closed(url):
    with pytest.raises(ValueError):
        VerifiedEntertainmentExecution.classify_official_route(url)


def test_confirmation_is_persona_bound_and_is_not_playback(tmp_path):
    service = VerifiedEntertainmentExecution(tmp_path)
    prepared = service.prepare(
        item={"title": "The Crown", "url": "https://www.netflix.com/title/81234567"},
        persona_id="persona_a",
    )
    with pytest.raises(PermissionError):
        service.confirm(prepared["execution_id"], persona_id="persona_b")
    confirmed = service.confirm(prepared["execution_id"], persona_id="persona_a")
    assert confirmed["status"] == "approved_for_device_attempt"
    assert confirmed["playback_verified"] is False
    assert confirmed["external_effect"] is False


def test_app_open_is_not_misreported_as_playback(tmp_path):
    service = VerifiedEntertainmentExecution(tmp_path)
    prepared = service.prepare(
        item={"title": "The Crown", "url": "https://www.netflix.com/title/81234567"},
        persona_id="persona_a",
    )
    service.confirm(prepared["execution_id"], persona_id="persona_a")
    result = service.record_attempt(prepared["execution_id"], persona_id="persona_a", receipt=_receipt())
    assert result["status"] == "provider_open_verified"
    assert result["provider_open_verified"] is True
    assert result["playback_verified"] is False


def test_playback_needs_explicit_title_and_playing_evidence(tmp_path):
    service = VerifiedEntertainmentExecution(tmp_path)
    prepared = service.prepare(
        item={"title": "The Crown", "url": "https://www.netflix.com/title/81234567"},
        persona_id="persona_a",
    )
    service.confirm(prepared["execution_id"], persona_id="persona_a")
    result = service.record_attempt(
        prepared["execution_id"],
        persona_id="persona_a",
        receipt=_receipt(),
        explicit_playback={"title": "The Crown", "playing": True},
    )
    assert result["status"] == "playback_verified"
    assert result["playback_verified"] is True


def test_continue_reuses_only_same_personas_verified_route(tmp_path):
    service = VerifiedEntertainmentExecution(tmp_path)
    prepared = service.prepare(
        item={"title": "The Crown", "url": "https://www.netflix.com/title/81234567"},
        persona_id="persona_a",
    )
    service.confirm(prepared["execution_id"], persona_id="persona_a")
    service.record_attempt(prepared["execution_id"], persona_id="persona_a", receipt=_receipt())

    continued = service.prepare_continue(persona_id="persona_a")
    assert continued["status"] == "awaiting_private_confirmation"
    assert continued["route_hash"] == prepared["route_hash"]
    with pytest.raises(ValueError):
        service.prepare_continue(persona_id="persona_b")
