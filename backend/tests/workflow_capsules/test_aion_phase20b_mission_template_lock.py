from backend.services.aion_mission_mode.mission_templates import (
    DEFAULT_HARD_BLOCKED_LANES,
    MISSION_TEMPLATE_REGISTRY,
    get_mission_template,
    list_mission_templates,
    template_hash,
    template_to_contract_seed,
)


def test_phase20b_template_registry_exists() -> None:
    assert "home_fixed_lead_campaign_v0" in MISSION_TEMPLATE_REGISTRY
    assert "home_fixed_quote_intake_v0" in MISSION_TEMPLATE_REGISTRY
    assert "weekly_marketing_pack_v0" in MISSION_TEMPLATE_REGISTRY
    assert "generic_business_build_pack_v0" in MISSION_TEMPLATE_REGISTRY


def test_phase20b_home_fixed_lead_campaign_template_has_required_shape() -> None:
    template = get_mission_template("home_fixed_lead_campaign_v0")

    assert template["name"] == "Home Fixed Lead Campaign"
    assert "Home Fixed lead generation campaign" in template["mission_goal"]
    assert "research" in template["allowed_autonomy_lanes"]
    assert "creation" in template["allowed_autonomy_lanes"]
    assert "internal_ops" in template["allowed_autonomy_lanes"]
    assert "external_action" in template["hard_blocked_lanes"]
    assert "financial_action" in template["hard_blocked_lanes"]
    assert "deployment_action" in template["hard_blocked_lanes"]
    assert "memory_mutation" in template["hard_blocked_lanes"]
    assert template["human_checkpoints"]
    assert template["template_hash"] == template_hash("home_fixed_lead_campaign_v0")


def test_phase20b_templates_default_to_safe_blocked_lanes() -> None:
    for template_id in MISSION_TEMPLATE_REGISTRY:
        template = get_mission_template(template_id)
        for lane in DEFAULT_HARD_BLOCKED_LANES:
            assert lane in template["hard_blocked_lanes"]

        checkpoint_steps = [
            step for step in template["steps"]
            if step["classification"] == "checkpoint_required"
        ]
        assert checkpoint_steps, f"{template_id} must include at least one checkpoint"


def test_phase20b_template_to_contract_seed_is_stable() -> None:
    first = template_to_contract_seed(
        "home_fixed_lead_campaign_v0",
        business_id="home_fixed",
        creator_id="kevin",
    )
    second = template_to_contract_seed(
        "home_fixed_lead_campaign_v0",
        business_id="home_fixed",
        creator_id="kevin",
    )

    assert first == second
    assert first["contract_seed_hash"] == second["contract_seed_hash"]


def test_phase20b_template_seed_is_preview_only_and_native_to_aion() -> None:
    seed = template_to_contract_seed(
        "home_fixed_lead_campaign_v0",
        business_id="home_fixed",
        creator_id="kevin",
    )

    assert seed["agent_mode"] == "checkpointed_autonomy"
    assert seed["proof_required"] is True
    assert seed["replay_required"] is True
    assert seed["ets_enabled"] is True
    assert seed["live_execution_enabled"] is False
    assert seed["external_writes_enabled"] is False
    assert seed["native_runtime_owner"] == "aion_core"
    assert seed["executor_name"] == "AION Pilot"


def test_phase20b_template_list_exposes_hashes_without_runtime_execution() -> None:
    templates = list_mission_templates()

    assert len(templates) >= 4
    assert all("template_hash" in item for item in templates)
    assert all("template_id" in item for item in templates)
    assert all("mission_goal" in item for item in templates)
