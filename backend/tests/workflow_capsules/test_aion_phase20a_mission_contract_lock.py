from backend.services.aion_mission_mode.mission_contract import (
    AionMissionContract,
    MissionCheckpoint,
    create_mission_contract,
    validate_no_live_side_effects,
)


def test_phase20a_mission_contract_can_be_created() -> None:
    contract = create_mission_contract(
        mission_id="mission_home_fixed_lead_campaign_001",
        mission_goal="Build a Home Fixed lead generation campaign",
        business_id="home_fixed",
        creator_id="kevin_robinson",
    )

    data = contract.to_dict()

    assert data["schema_version"] == "aion.mission_contract.v0"
    assert data["mission_id"] == "mission_home_fixed_lead_campaign_001"
    assert data["mission_goal"] == "Build a Home Fixed lead generation campaign"
    assert data["business_id"] == "home_fixed"
    assert data["agent_mode"] == "checkpointed_autonomy"
    assert data["mission_hash"]


def test_phase20a_contract_hash_is_deterministic() -> None:
    first = create_mission_contract(
        mission_id="mission_001",
        mission_goal="Prepare quote intake workflow",
        business_id="home_fixed",
        creator_id="kevin_robinson",
    )

    second = create_mission_contract(
        mission_id="mission_001",
        mission_goal="Prepare quote intake workflow",
        business_id="home_fixed",
        creator_id="kevin_robinson",
    )

    assert first.mission_hash() == second.mission_hash()


def test_phase20a_default_lanes_are_safe_and_block_live_risk_lanes() -> None:
    contract = AionMissionContract(
        mission_id="mission_002",
        mission_goal="Build campaign draft",
        business_id="home_fixed",
        creator_id="kevin_robinson",
    )

    assert "research" in contract.allowed_autonomy_lanes
    assert "creation" in contract.allowed_autonomy_lanes
    assert "internal_ops" in contract.allowed_autonomy_lanes

    assert "external_action" in contract.hard_blocked_lanes
    assert "financial_action" in contract.hard_blocked_lanes
    assert "legal_action" in contract.hard_blocked_lanes
    assert "deployment_action" in contract.hard_blocked_lanes
    assert "memory_mutation" in contract.hard_blocked_lanes


def test_phase20a_human_checkpoints_are_part_of_contract_hash() -> None:
    base = create_mission_contract(
        mission_id="mission_003",
        mission_goal="Build Home Fixed lead campaign",
        business_id="home_fixed",
        creator_id="kevin_robinson",
    )

    with_checkpoint = create_mission_contract(
        mission_id="mission_003",
        mission_goal="Build Home Fixed lead campaign",
        business_id="home_fixed",
        creator_id="kevin_robinson",
        human_checkpoints=[
            MissionCheckpoint(
                checkpoint_id="checkpoint_approve_advert",
                title="Approve advert before publish",
                description="Human approval required before public advert posting.",
                required_before_step_id="step_publish_advert",
                lane="external_action",
                action_type="post_social",
            )
        ],
    )

    assert base.mission_hash() != with_checkpoint.mission_hash()


def test_phase20a_contract_has_no_live_side_effects_enabled() -> None:
    contract = create_mission_contract(
        mission_id="mission_004",
        mission_goal="Prepare campaign preview",
        business_id="home_fixed",
        creator_id="kevin_robinson",
    )

    assert validate_no_live_side_effects(contract) is True
    assert contract.live_external_writes_enabled is False
    assert contract.live_payment_enabled is False
    assert contract.live_booking_enabled is False
    assert contract.live_deployment_enabled is False
    assert contract.live_reputation_mutation_enabled is False
    assert contract.live_chain_write_enabled is False


def test_phase20a_contract_has_privacy_and_compliance_flags() -> None:
    contract = create_mission_contract(
        mission_id="mission_005",
        mission_goal="Prepare lead workflow",
        business_id="home_fixed",
        creator_id="kevin_robinson",
    )

    assert contract.data_retention_policy == "mission_scoped"
    assert contract.external_communication_consent_required is True
    assert contract.proof_sharing_enabled is False
