from __future__ import annotations

from backend.services.aion_mission_mode.home_fixed_founder_demo import (
    ALWAYS_APPROVAL_ACTIONS,
    build_demo_safety_matrix,
    build_founder_demo_outputs,
    build_home_fixed_founder_demo_contract,
    build_home_fixed_founder_demo_plan,
    canonical_hash,
    classify_demo_step,
)


def test_phase20j_plan_contains_home_fixed_vertical():
    plan = build_home_fixed_founder_demo_plan()

    assert plan["business_id"] == "home_fixed"
    assert plan["vertical"] == "home_repair_roofing_pergola"
    assert plan["plan_hash"].startswith("sha256:")


def test_phase20j_plan_contains_required_demo_steps():
    plan = build_home_fixed_founder_demo_plan()
    action_types = {step["action_type"] for step in plan["steps"]}

    assert "draft_offer" in action_types
    assert "draft_landing_page" in action_types
    assert "prepare_vercel_preview" in action_types
    assert "prepare_domain_checkout_preview" in action_types
    assert "buy_domain" in action_types
    assert "deploy_to_production" in action_types
    assert "publish_facebook_post" in action_types
    assert "start_ad_campaign" in action_types


def test_phase20j_always_approval_actions_are_gated():
    plan = build_home_fixed_founder_demo_plan()

    for step in plan["steps"]:
        classified = classify_demo_step(step)
        if step["action_type"] in ALWAYS_APPROVAL_ACTIONS:
            assert classified["effective_control_mode"] == "human_approval_required"
            assert classified["blocked_live_execution"] is True


def test_phase20j_human_profile_setup_is_human_task():
    plan = build_home_fixed_founder_demo_plan()
    step = next(s for s in plan["steps"] if s["action_type"] == "create_real_facebook_account")

    classified = classify_demo_step(step)

    assert classified["effective_control_mode"] == "human_task_required"
    assert classified["blocked_live_execution"] is True


def test_phase20j_demo_safety_matrix_counts_gated_steps():
    plan = build_home_fixed_founder_demo_plan()
    matrix = build_demo_safety_matrix(plan)

    assert matrix["approval_required_count"] >= 5
    assert matrix["human_task_required_count"] >= 1
    assert matrix["external_side_effects_allowed_without_approval"] is False
    assert matrix["demo_safety_matrix_hash"].startswith("sha256:")


def test_phase20j_outputs_are_previews_not_live_side_effects():
    plan = build_home_fixed_founder_demo_plan()
    matrix = build_demo_safety_matrix(plan)
    bundle = build_founder_demo_outputs(plan, matrix)
    outputs = bundle["outputs"]

    assert outputs["website_project_preview"]["created_locally"] is True
    assert outputs["website_project_preview"]["production_deployed"] is False
    assert outputs["domain_checkout_preview"]["domain_purchased"] is False
    assert outputs["public_post_preview"]["published"] is False
    assert outputs["ad_campaign_preview"]["started"] is False


def test_phase20j_receipt_proves_no_unapproved_actions():
    contract = build_home_fixed_founder_demo_contract()
    receipt = contract["receipt"]

    assert receipt["no_unapproved_payment"] is True
    assert receipt["no_unapproved_deploy"] is True
    assert receipt["no_unapproved_publish"] is True
    assert receipt["no_unapproved_send"] is True
    assert receipt["no_unapproved_booking"] is True
    assert receipt["ets_preview_only"] is True


def test_phase20j_contract_contains_boardroom_safety_message():
    contract = build_home_fixed_founder_demo_contract()

    assert contract["boardroom_message"] == "AION completed safe work autonomously and stopped itself before doing anything risky."
    assert contract["literal_safety_message"] == "AION stopped itself before doing anything risky."


def test_phase20j_no_live_side_effect_flags_are_false():
    plan = build_home_fixed_founder_demo_plan()

    assert plan["live_payment_created"] is False
    assert plan["live_booking_created"] is False
    assert plan["live_escrow_created"] is False
    assert plan["live_external_message_sent"] is False
    assert plan["live_production_deploy_created"] is False
    assert plan["live_reputation_mutated"] is False


def test_phase20j_contract_hash_is_deterministic():
    left = build_home_fixed_founder_demo_contract()
    right = build_home_fixed_founder_demo_contract()

    assert left["founder_demo_contract_hash"] == right["founder_demo_contract_hash"]


def test_phase20j_canonical_hash_is_key_order_stable():
    assert canonical_hash({"b": 2, "a": 1}) == canonical_hash({"a": 1, "b": 2})


def test_phase20j_demo_contract_binds_plan_matrix_outputs_and_receipt():
    contract = build_home_fixed_founder_demo_contract()

    assert contract["plan"]["plan_hash"].startswith("sha256:")
    assert contract["safety_matrix"]["demo_safety_matrix_hash"].startswith("sha256:")
    assert contract["outputs"]["outputs_hash"].startswith("sha256:")
    assert contract["receipt"]["founder_demo_receipt_hash"].startswith("sha256:")
