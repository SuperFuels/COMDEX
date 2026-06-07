import pytest

from backend.services.aion_mission_mode.llm_planner_adapter import (
    PlannerAdapterError,
    PlannerBypassViolation,
    compile_mission_contract_from_plan,
    compile_structured_plan_proposal,
)


def sample_plan():
    return {
        "plan_title": "Build Home Fixed lead generation system",
        "steps": [
            {
                "title": "Draft offer",
                "description": "Create a safe internal offer draft.",
                "action_type": "draft_offer",
                "lane": "creation",
            },
            {
                "title": "Buy domain",
                "description": "Prepare a domain purchase approval step.",
                "action_type": "buy_domain",
                "provider": "domain_provider",
                "estimated_cost": 11.99,
            },
            {
                "title": "Create Facebook page",
                "description": "Human must create or connect the page.",
                "action_type": "create_real_facebook_account",
            },
        ],
    }


def compile_sample(provider="mock_planner"):
    return compile_structured_plan_proposal(
        mission_id="mission_homefixed",
        mission_run_id="run_001",
        business_id="home_fixed",
        provider=provider,
        user_goal="Build and market Home Fixed",
        raw_model_plan=sample_plan(),
    )


def test_phase20k_accepts_supported_mock_planner():
    proposal = compile_sample()
    assert proposal["planner_output_type"] == "structured_plan_proposal_only"
    assert proposal["model_may_execute"] is False
    assert proposal["model_may_call_raw_tools"] is False
    assert proposal["model_may_mutate_runtime"] is False
    assert proposal["proposal_hash"].startswith("sha256:")


def test_phase20k_accepts_gemma_local_provider():
    proposal = compile_sample("gemma_local")
    assert proposal["planner_provider"] == "gemma_local"


def test_phase20k_accepts_openai_frontier_provider():
    proposal = compile_sample("openai_frontier")
    assert proposal["planner_provider"] == "openai_frontier"


def test_phase20k_rejects_unknown_provider():
    with pytest.raises(PlannerAdapterError):
        compile_sample("unknown_model")


def test_phase20k_rejects_raw_tool_call_key():
    bad_plan = sample_plan()
    bad_plan["steps"][0]["raw_tool_call"] = {"tool": "send_email"}

    with pytest.raises(PlannerBypassViolation):
        compile_structured_plan_proposal(
            mission_id="m",
            mission_run_id="r",
            business_id="b",
            provider="mock_planner",
            user_goal="bad",
            raw_model_plan=bad_plan,
        )


def test_phase20k_rejects_execute_now_key_nested():
    bad_plan = sample_plan()
    bad_plan["steps"][0]["nested"] = {"execute_now": True}

    with pytest.raises(PlannerBypassViolation):
        compile_structured_plan_proposal(
            mission_id="m",
            mission_run_id="r",
            business_id="b",
            provider="mock_planner",
            user_goal="bad",
            raw_model_plan=bad_plan,
        )


def test_phase20k_requires_non_empty_steps():
    with pytest.raises(PlannerAdapterError):
        compile_structured_plan_proposal(
            mission_id="m",
            mission_run_id="r",
            business_id="b",
            provider="mock_planner",
            user_goal="empty",
            raw_model_plan={"steps": []},
        )


def test_phase20k_safe_step_defaults_autonomous():
    proposal = compile_sample()
    assert proposal["steps"][0]["default_control"] == "autonomous"


def test_phase20k_domain_purchase_becomes_approval_required():
    proposal = compile_sample()
    domain_step = proposal["steps"][1]
    assert domain_step["default_control"] == "human_approval_required"
    assert domain_step["external_side_effect"] is True
    assert domain_step["payload_required_later"] is True
    assert domain_step["risk_level"] == "high"


def test_phase20k_human_account_step_becomes_human_task():
    proposal = compile_sample()
    human_step = proposal["steps"][2]
    assert human_step["default_control"] == "human_task_required"


def test_phase20k_step_hashes_are_deterministic():
    a = compile_sample()
    b = compile_sample()
    assert [s["step_hash"] for s in a["steps"]] == [s["step_hash"] for s in b["steps"]]
    assert a["proposal_hash"] == b["proposal_hash"]


def test_phase20k_compiles_to_deterministic_contract():
    proposal = compile_sample()
    contract = compile_mission_contract_from_plan(proposal)

    assert contract["compiled_contract_state"] == "requires_plan_matrix_review"
    assert contract["must_pass_plan_approval_matrix"] is True
    assert contract["must_pass_approval_lattice"] is True
    assert contract["must_pass_autonomy_budget"] is True
    assert contract["must_pass_expiry_revocation"] is True
    assert contract["must_pass_external_tool_gateway"] is True
    assert contract["live_external_side_effects_allowed"] is False
    assert contract["mission_contract_hash"].startswith("sha256:")


def test_phase20k_contract_rejects_execution_enabled_proposal():
    proposal = compile_sample()
    proposal["model_may_execute"] = True

    with pytest.raises(PlannerBypassViolation):
        compile_mission_contract_from_plan(proposal)


def test_phase20k_contract_rejects_raw_tool_enabled_proposal():
    proposal = compile_sample()
    proposal["model_may_call_raw_tools"] = True

    with pytest.raises(PlannerBypassViolation):
        compile_mission_contract_from_plan(proposal)


def test_phase20k_contract_rejects_runtime_mutation_enabled_proposal():
    proposal = compile_sample()
    proposal["model_may_mutate_runtime"] = True

    with pytest.raises(PlannerBypassViolation):
        compile_mission_contract_from_plan(proposal)
