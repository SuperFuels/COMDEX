from fastapi.testclient import TestClient

from backend.main import app
from backend.services.aion_mission_mode.business_context_mission_map import (
    build_business_context_mission_map,
)


def _brand():
    return {
        "brandMap": {
            "brandVoice": {"toneOfVoice": "clear, trusted, practical"},
            "brandStory": {"howStarted": "local home repair support"},
            "targetAudience": "homeowners and landlords",
            "offer": "reliable property maintenance",
            "channels": ["facebook", "twitter/x"],
        }
    }


def _marketing():
    return {
        "objective": "grow qualified local enquiries",
        "targetAudience": "homeowners in Almeria and Murcia",
        "offer": "photo-first repair quote",
        "channels": "Facebook, Google Business Profile, Twitter/X",
        "hardRules": "No public posting without approval.",
    }


def test_phase23b_context_map_binds_brand_and_marketing_context():
    result = build_business_context_mission_map(
        business_id="home-fixed",
        mission_id="mission_23b",
        mission_run_id="run_23b",
        user_goal="produce a marketing plan and setup Twitter/X channel",
        plan_text="Twitter/X channel setup",
        brand_foundation_state=_brand(),
        marketing_form=_marketing(),
        marketing_summary={},
        available_vault_requirements=[],
    )

    ctx = result["business_context"]
    assert ctx["brand_foundation_available"] is True
    assert ctx["marketing_form_available"] is True
    assert ctx["tone_of_voice"] == "clear, trusted, practical"
    assert ctx["marketing_objective"] == "grow qualified local enquiries"
    assert ctx["context_hash"].startswith("sha256:")


def test_phase23b_twitter_setup_pauses_for_vault_or_human_task_when_missing():
    result = build_business_context_mission_map(
        business_id="home-fixed",
        mission_id="mission_23b",
        mission_run_id="run_23b",
        user_goal="Twitter/X channel setup",
        plan_text="setup twitter posts and channel",
        brand_foundation_state=_brand(),
        marketing_form=_marketing(),
        marketing_summary={},
        available_vault_requirements=[],
    )

    node = result["task_nodes"][0]
    assert node["title"] == "Twitter/X channel setup"
    assert node["decision"] == "human_task_required"
    assert node["credential_required"] is True
    assert result["human_task_cards"]
    assert result["credential_required_cards"]
    assert "vault.twitter_x.oauth" in result["human_task_cards"][0]["required_vault_handles"]


def test_phase23b_twitter_setup_can_stage_when_vault_ref_exists_but_still_blocks_live_actions():
    result = build_business_context_mission_map(
        business_id="home-fixed",
        mission_id="mission_23b",
        mission_run_id="run_23b",
        user_goal="Twitter/X channel setup",
        plan_text="setup twitter posts and channel",
        brand_foundation_state=_brand(),
        marketing_form=_marketing(),
        marketing_summary={},
        available_vault_requirements=["vault.twitter_x.oauth"],
    )

    twitter_nodes = [
        node for node in result["task_nodes"]
        if node.get("provider") == "twitter_x"
    ]

    assert twitter_nodes
    node = twitter_nodes[0]

    assert node["decision"] == "staged_external"
    assert node["staged_external_allowed"] is True
    assert node["live_public_post_requires_exact_approval"] is True
    assert node["live_external_side_effects_allowed"] is False

    twitter_human_cards = [
        card for card in result["human_task_cards"]
        if "twitter" in str(card).lower() or "twitter_x" in str(card).lower()
    ]

    assert twitter_human_cards == []


def test_phase23b_endpoint_returns_context_map_and_no_raw_credentials():
    client = TestClient(app)

    response = client.post(
        "/api/local-node/aion/pilot/mission-preview",
        json={
            "business_id": "home-fixed",
            "mission_id": "mission_23b_endpoint",
            "mission_run_id": "run_23b_endpoint",
            "user_goal": "produce a marketing plan for home fixed and setup Twitter/X channel",
            "plan_text": "Twitter/X channel setup",
            "brand_foundation_state": _brand(),
            "marketing_form": _marketing(),
            "available_vault_requirements": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["payload_type"] == "aion_pilot_mission_preview"
    assert payload["business_context_mission_map"]["payload_type"] == "aion_business_context_mission_map"
    assert payload["context_task_nodes"]
    assert payload["human_task_cards"]
    assert payload["credential_required_cards"]
    assert payload["safety"]["live_external_side_effects_enabled"] is False

    dumped = str(payload).lower()
    assert "password_value" not in dumped
    assert "access_token_value" not in dumped
    assert "secret_value" not in dumped


def test_phase23b_frontend_passes_brand_marketing_context_if_payload_builder_exists():
    text = open("desktop/mac/src/app.js", encoding="utf-8").read()

    assert "state.brandFoundationState" in text
    assert "state.marketingForm" in text
    assert "state.marketingSummary" in text
