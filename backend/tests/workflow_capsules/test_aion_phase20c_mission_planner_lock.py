from backend.services.aion_mission_mode.mission_contract import (
    AionMissionContract,
    MissionCheckpoint,
    MissionMode,
)
from backend.services.aion_mission_mode.mission_planner import (
    build_deterministic_mission_plan,
    create_home_fixed_lead_campaign_plan,
)


def make_contract() -> AionMissionContract:
    return AionMissionContract(
        mission_id="mission_home_fixed_lead_campaign_001",
        mission_goal="Build a Home Fixed lead generation campaign for roof repairs and outdoor living work.",
        business_id="home_fixed",
        creator_id="kevin",
        agent_mode=MissionMode.CHECKPOINTED_AUTONOMY,
        allowed_autonomy_lanes=[
            "research",
            "creation",
            "internal_ops",
        ],
        hard_blocked_lanes=[
            "financial_action",
            "legal_action",
            "deployment_action",
        ],
        human_checkpoints=[
            MissionCheckpoint(
                checkpoint_id="checkpoint_publish_approval",
                title="Approve campaign before publishing",
                description="Approve campaign before publishing.",
                required_before_step_id="step_publish_advert",
                lane="external_action",
                action_type="publish_advert",
                required_action_type="publish_advert",
            )
        ],
        approval_required_actions=[
            "publish_advert",
            "send_customer_message",
            "spend_money",
            "create_booking",
            "deploy_live_page",
            "take_payment",
            "create_escrow",
            "dispatch_worker",
        ],
        max_runtime_seconds=1800,
        max_tool_calls=40,
        max_cost=0.0,
        proof_required=True,
        replay_required=True,
        ets_enabled=True,
        data_retention_policy="mission_scoped",
        external_communication_consent_required=True,
        proof_sharing_enabled=False,
    )


def test_phase20c_planner_returns_stable_plan_hash() -> None:
    contract = make_contract()

    first = build_deterministic_mission_plan(
        contract=contract,
        template_id="home_fixed_lead_campaign_v0",
    )
    second = build_deterministic_mission_plan(
        contract=contract,
        template_id="home_fixed_lead_campaign_v0",
    )

    assert first["plan_hash"] == second["plan_hash"]
    assert len(first["plan_hash"]) == 64


def test_phase20c_home_fixed_plan_contains_expected_outputs() -> None:
    plan = create_home_fixed_lead_campaign_plan()

    assert plan["business_id"] == "home_fixed"
    assert plan["created_by"] == "aion_pilot"
    assert "campaign_offer" in plan["final_output_targets"]
    assert "advert_draft" in plan["final_output_targets"]
    assert "landing_page_copy" in plan["final_output_targets"]
    assert "workflow_preview" in plan["final_output_targets"]
    assert "agentmap_preview" in plan["final_output_targets"]


def test_phase20c_plan_marks_safe_steps_autonomous() -> None:
    plan = create_home_fixed_lead_campaign_plan()

    safe_steps = [
        step for step in plan["steps"]
        if step["action_type"] in {
            "research_service_angle",
            "draft_offer",
            "draft_facebook_advert",
            "draft_landing_page_copy",
            "create_workflow_preview",
            "create_agentmap_preview",
        }
    ]

    assert safe_steps
    assert all(step["decision"] == "safe_autonomous" for step in safe_steps)
    assert all(step["requires_checkpoint"] is False for step in safe_steps)


def test_phase20c_plan_adds_checkpoint_for_publish_action() -> None:
    plan = create_home_fixed_lead_campaign_plan()

    publish_steps = [
        step for step in plan["steps"]
        if step["action_type"] == "publish_advert"
    ]

    assert publish_steps
    assert publish_steps[0]["decision"] == "checkpoint_required"
    assert publish_steps[0]["requires_checkpoint"] is True
    assert plan["checkpoints"]
    assert plan["checkpoints"][0]["action_type"] == "publish_advert"
    assert len(plan["checkpoints"][0]["payload_hash"]) == 64


def test_phase20c_plan_is_preview_only_no_live_side_effects() -> None:
    plan = create_home_fixed_lead_campaign_plan()

    assert plan["dry_run_only"] is True
    assert plan["live_side_effects_enabled"] is False

    forbidden = [
        "send_whatsapp_live",
        "send_email_live",
        "capture_payment_live",
        "create_booking_live",
        "deploy_production_live",
        "write_live_reputation",
    ]

    dumped = str(plan)
    for token in forbidden:
        assert token not in dumped


def test_phase20c_artifact_steps_have_business_sub_container_targets() -> None:
    plan = create_home_fixed_lead_campaign_plan()

    artifact_steps = [step for step in plan["steps"] if step["produces_artifact"]]

    assert artifact_steps
    for step in artifact_steps:
        assert step["artifact_type"]
        assert step["preferred_sub_container"] in {
            "campaigns",
            "workflows",
            "agentmaps",
            "approvals",
            "quotes",
            "reports",
            "evidence",
            "exports",
            "receipts",
        }
