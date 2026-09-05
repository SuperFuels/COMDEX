from __future__ import annotations

import pytest

from backend.modules.aion_fabric.screen_fusion import ScreenUnderstandingFusion
from backend.modules.aion_fabric.voice import parse_voice_intent


def test_screen_fusion_detects_subtitles_scoreboard_and_never_identifies_people(tmp_path):
    service = ScreenUnderstandingFusion(tmp_path)
    result = service.fuse(
        perception={
            "texts": ["REAL MADRID 2 - 1 BARCELONA", "78:42", "What a finish from the striker"],
            "text_observations": [
                {"text": "REAL MADRID 2 - 1 BARCELONA", "confidence": 0.98, "y": 0.86},
                {"text": "What a finish from the striker", "confidence": 0.94, "x": 0.2, "width": 0.6, "y": 0.08},
            ],
            "labels": [{"label": "people", "confidence": 0.9}, {"label": "sports", "confidence": 0.88}],
            "inference": {"surface": "media_app", "confidence": 0.8},
        },
        device_state={"foreground_app_id": "sports.app", "foreground_app_title": "Live Sports"},
        provider_metadata={
            "provider": "youtube",
            "content_id": "dQw4w9WgXcQ",
            "title": "Official programme title",
            "metadata_status": "official_api_verified",
            "availability_verified": False,
        },
    )
    assert result["subtitles"]["lines"] == ["What a finish from the striker"]
    assert result["scoreboard"]["detected"] is True
    assert result["scoreboard"]["clock"] == "78:42"
    assert result["entities"]["unknown_people_visible"] is True
    assert result["entities"]["identity_inferred"] is False
    assert result["privacy"]["source_pixels_retained"] is False
    assert result["provider_metadata"]["title"] == "Official programme title"
    assert result["provider_metadata"]["availability_verified"] is False


def test_screen_fusion_detects_products_and_requires_private_confirmation(tmp_path):
    result = ScreenUnderstandingFusion(tmp_path).fuse(
        perception={
            "texts": ["Extendable ladder", "€129.99", "Add to basket"],
            "labels": [{"label": "product", "confidence": 0.82}],
            "inference": {"surface": "web_browser", "confidence": 0.9},
        },
        device_state={"foreground_app_id": "com.webos.app.browser", "foreground_app_title": "Browser"},
    )
    assert result["products"]["detected"] is True
    assert result["products"]["prices"] == ["€129.99"]
    assert result["products"]["requires_private_confirmation"] is True


def test_screen_fusion_detects_game_hud_and_accepts_scoped_owner_correction(tmp_path):
    service = ScreenUnderstandingFusion(tmp_path)
    result = service.fuse(
        perception={
            "texts": ["Mission complete", "Score 2500", "Health 80"],
            "labels": [],
            "inference": {"surface": "games", "confidence": 0.93},
        },
        device_state={"foreground_app_title": "GeForce NOW"},
    )
    assert result["game"]["detected"] is True
    corrected = service.correct(
        observation_id=result["observation_id"],
        field="scene",
        value="The mission has just completed",
        persona_id="persona_test",
    )
    assert corrected["corrected_by_owner"] is True
    assert corrected["corrections"][0]["value"] == "The mission has just completed"
    with pytest.raises(ValueError, match="not supported"):
        service.correct(observation_id=result["observation_id"], field="person_identity", value="Alex", persona_id="persona_test")


def test_screen_fusion_extracts_bounded_programme_title_candidates_only_on_media(tmp_path):
    service = ScreenUnderstandingFusion(tmp_path)
    result = service.fuse(
        perception={
            "texts": ["The Crown", "Play", "12:34", "€9.99"],
            "text_observations": [
                {"text": "The Crown", "confidence": 0.96, "height": 0.08, "width": 0.42},
                {"text": "Play", "confidence": 0.99, "height": 0.04, "width": 0.12},
                {"text": "12:34", "confidence": 0.99, "height": 0.04, "width": 0.12},
                {"text": "€9.99", "confidence": 0.99, "height": 0.04, "width": 0.12},
            ],
            "inference": {"surface": "netflix", "confidence": 0.9},
        },
        device_state={"foreground_app_title": "Netflix"},
    )
    assert [item["title"] for item in result["programme_candidates"]] == ["The Crown"]

    browser = service.fuse(
        perception={
            "text_observations": [{"text": "The Crown", "confidence": 0.96, "height": 0.08, "width": 0.42}],
            "inference": {"surface": "web_browser", "confidence": 0.9},
        },
        device_state={"foreground_app_title": "Browser"},
    )
    assert browser["programme_candidates"] == []


def test_screen_fusion_reports_only_explicit_cooking_terms_and_bounded_object_labels(tmp_path):
    result = ScreenUnderstandingFusion(tmp_path).fuse(
        perception={
            "texts": ["Chop the onion and garlic, then fry in oil"],
            "labels": [
                {"label": "onion", "confidence": 0.91},
                {"label": "frying pan", "confidence": 0.88},
                {"label": "person", "confidence": 0.99},
                {"label": "uncertain utensil", "confidence": 0.31},
            ],
            "inference": {"surface": "media_app", "confidence": 0.8},
        },
        device_state={"foreground_app_title": "Cooking programme"},
    )

    assert result["cooking"]["ingredients"] == ["garlic", "oil", "onion"]
    assert result["cooking"]["techniques"] == ["chop", "fry"]
    assert result["objects"]["labels"] == ["onion", "frying pan"]
    assert result["objects"]["identity_inferred"] is False
    assert "person" not in result["objects"]["labels"]
    assert "uncertain utensil" not in result["objects"]["labels"]


def test_screen_evidence_voice_queries_and_product_claim_route_are_explicit():
    assert parse_voice_intent("Pilot, what ingredients are they using?").arguments == {"kind": "ingredients"}
    assert parse_voice_intent("Pilot, what technique are they using?").arguments == {"kind": "technique"}
    assert parse_voice_intent("Pilot, what objects can you see?").arguments == {"kind": "objects"}
    product = parse_voice_intent("Pilot, fact check that product claim")
    assert product.action == "live_fact_check"
    assert product.arguments == {"kind": "product_claim"}
