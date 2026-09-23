from __future__ import annotations

import io
import json

from backend.modules.aion_fabric.provider_metadata import ProviderMetadataResolver


def test_youtube_reference_is_normalized_without_claiming_entitlement(tmp_path, monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    result = ProviderMetadataResolver(tmp_path).resolve(
        ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
        app_id="youtube.leanback.v4",
        app_title="YouTube",
    )

    assert result["provider"] == "youtube"
    assert result["content_id"] == "dQw4w9WgXcQ"
    assert result["metadata_status"] == "provider_identifier_only"
    assert result["provider_api_called"] is False
    assert result["availability_verified"] is False
    assert result["account_entitlement_verified"] is False


def test_youtube_official_api_enriches_metadata_when_owner_supplies_key(tmp_path, monkeypatch):
    response = {
        "items": [{
            "id": "dQw4w9WgXcQ",
            "snippet": {
                "title": "Example title",
                "channelTitle": "Example channel",
                "publishedAt": "2026-01-01T00:00:00Z",
                "liveBroadcastContent": "none",
            },
            "contentDetails": {"duration": "PT3M33S", "caption": "true"},
            "status": {"embeddable": True, "privacyStatus": "public"},
        }]
    }

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.close()

    monkeypatch.setenv("YOUTUBE_API_KEY", "test-key")
    monkeypatch.setattr(
        "backend.modules.aion_fabric.provider_metadata.urllib.request.urlopen",
        lambda request, timeout=0: Response(json.dumps(response).encode()),
    )
    result = ProviderMetadataResolver(tmp_path).resolve(
        ["https://youtu.be/dQw4w9WgXcQ"]
    )

    assert result["metadata_status"] == "official_api_verified"
    assert result["title"] == "Example title"
    assert result["captions_available"] is True
    assert result["provider_api_called"] is True
    assert result["account_entitlement_verified"] is False


def test_netflix_reference_exposes_native_moment_boundary_not_media_copying(tmp_path):
    result = ProviderMetadataResolver(tmp_path).resolve(
        ["https://www.netflix.com/title/81234567"], app_title="Netflix"
    )

    assert result["provider"] == "netflix"
    assert result["content_id"] == "81234567"
    assert result["native_share"] == "netflix_mobile_moments"
    assert result["availability_verified"] is False
    assert any("does not copy" in item for item in result["limitations"])


def test_repeated_screen_title_can_receive_strict_public_catalogue_identity(tmp_path, monkeypatch):
    response = [{
        "score": 1.0,
        "show": {
            "id": 3594,
            "name": "The Crown",
            "type": "Scripted",
            "language": "English",
            "premiered": "2016-11-04",
            "ended": "2023-12-14",
            "url": "https://www.tvmaze.com/shows/3594/the-crown",
        },
    }]

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.close()

    calls = []

    def open_catalogue(request, timeout=0):
        calls.append(request.full_url)
        return Response(json.dumps(response).encode())

    monkeypatch.setattr(
        "backend.modules.aion_fabric.provider_metadata.urllib.request.urlopen",
        open_catalogue,
    )
    resolver = ProviderMetadataResolver(tmp_path)
    result = resolver.resolve(
        [],
        app_title="Netflix",
        programme_candidates=["The Crown"],
    )

    assert result["title"] == "The Crown"
    assert result["metadata_status"] == "public_catalogue_exact_match"
    assert result["catalogue_identity_verified"] is True
    assert result["current_playback_verified"] is False
    assert result["availability_verified"] is False
    assert result["account_entitlement_verified"] is False
    assert result["application_provider_hint"] == "netflix"
    assert "TVmaze" in result["attribution"]

    cached = resolver.resolve([], app_title="Netflix", programme_candidates=["The Crown"])
    assert cached["catalogue_cache_hit"] is True
    assert len(calls) == 1


def test_public_catalogue_refuses_ambiguous_exact_title(tmp_path, monkeypatch):
    response = [
        {"show": {"id": 1, "name": "Neighbours", "url": "https://www.tvmaze.com/shows/1/neighbours"}},
        {"show": {"id": 2, "name": "Neighbours", "url": "https://www.tvmaze.com/shows/2/neighbours"}},
    ]

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.close()

    monkeypatch.setattr(
        "backend.modules.aion_fabric.provider_metadata.urllib.request.urlopen",
        lambda request, timeout=0: Response(json.dumps(response).encode()),
    )
    result = ProviderMetadataResolver(tmp_path).resolve(
        [], app_title="Netflix", programme_candidates=["Neighbours"]
    )

    assert result["metadata_status"] == "public_catalogue_ambiguous"
    assert result["catalogue_identity_verified"] is False
    assert result.get("title") is None
