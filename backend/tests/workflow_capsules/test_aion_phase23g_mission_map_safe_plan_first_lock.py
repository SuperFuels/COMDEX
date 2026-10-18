from pathlib import Path

from backend.services.aion_mission_mode.business_context_mission_map import (
    build_business_context_mission_map,
)

APP = Path("desktop/mac/src/app.js")


def test_phase23g_generic_marketing_context_does_not_force_facebook_provider_node():
    result = build_business_context_mission_map(
        business_id="home-fixed",
        mission_id="mission_23g",
        mission_run_id="run_23g",
        user_goal="produce a marketing plan for home fixed and execute the plan to grow the business",
        plan_text="Marketing objective, target audience, positioning, channel plan, content plan",
        brand_foundation_state={},
        marketing_form={
            "channels": "Facebook, Google Business Profile, Twitter/X",
            "objective": "grow enquiries",
        },
        marketing_summary={},
        available_vault_requirements=[],
    )

    assert result["task_nodes"] == []
    assert result["human_task_cards"] == []
    assert result["credential_required_cards"] == []


def test_phase23g_explicit_twitter_channel_setup_still_creates_vault_checkpoint():
    result = build_business_context_mission_map(
        business_id="home-fixed",
        mission_id="mission_23g",
        mission_run_id="run_23g",
        user_goal="setup Twitter/X channel",
        plan_text="Twitter/X channel setup",
        brand_foundation_state={},
        marketing_form={},
        marketing_summary={},
        available_vault_requirements=[],
    )

    assert result["task_nodes"]
    assert result["task_nodes"][0]["provider"] == "twitter_x"
    assert result["credential_required_cards"]


def test_phase23g_frontend_queue_uses_backend_safe_plan_nodes_first():
    text = APP.read_text()

    assert "safePlanNodes" in text
    assert "source: \"backend_mission_plan\"" in text
    assert "...safePlanNodes" in text
    assert "...taskNodes" in text
    assert "const nextMissionLoopQueue = [" in text
    assert "pilotState.mission_loop_queue = nextMissionLoopQueue" in text


def test_phase23g_old_continue_approve_buttons_route_to_backend_when_approved():
    text = APP.read_text()

    assert 'target.closest("[data-aion-pilot-feedback-approve]")' in text
    assert 'contract_status === "approved_for_safe_work"' in text
    assert "runAionPilotSafeWorkPreview();" in text
