from backend.services.aion_mission_mode.external_tool_gateway import (
    create_capability_registry,
    get_capability,
)
from backend.services.aion_mission_mode.pilot_capability_adapter import (
    adapt_department_queue_item_to_gateway_request,
    create_adapter_demo_item,
    evaluate_department_queue_item_gateway_access,
    gateway_capability_for_department_capability,
    local_tool_id_for_department_capability,
)


def test_phase23o_adapter_reuses_existing_external_tool_gateway_registry():
    registry = create_capability_registry()

    assert registry["schema_version"] == "aion.external_tool_gateway.registry.v0"
    assert get_capability(registry=registry, tool_name="generate_copy") is not None
    assert get_capability(registry=registry, tool_name="publish_facebook_post") is not None
    assert get_capability(registry=registry, tool_name="mutate_provider_account") is not None


def test_phase23o_marketing_campaign_plan_maps_to_safe_gateway_capability():
    item = create_adapter_demo_item(department_id="marketing", capability="campaign.plan")
    adapted = adapt_department_queue_item_to_gateway_request(queue_item=item)

    assert adapted["adapted"] is True
    assert adapted["department_id"] == "marketing"
    assert adapted["department_capability"] == "campaign.plan"
    assert adapted["gateway_tool_name"] == "generate_copy"
    assert adapted["gateway_request"]["tool_name"] == "generate_copy"
    assert adapted["adapter_hash"].startswith("sha256:")


def test_phase23o_social_post_draft_maps_to_staged_external_gateway_capability():
    item = create_adapter_demo_item(department_id="marketing", capability="social.post_draft")
    evaluated = evaluate_department_queue_item_gateway_access(
        queue_item=item,
        evaluation_time=100,
    )

    assert evaluated["gateway_tool_name"] == "prepare_facebook_post"
    assert evaluated["gateway_evaluation"]["allowed"] is True
    assert evaluated["gateway_evaluation"]["tool_mode"] == "staged_external"
    assert evaluated["gateway_evaluation"]["gateway_state"] == "allowed"


def test_phase23o_browser_research_maps_to_read_only_external():
    item = create_adapter_demo_item(department_id="marketing", capability="seo.plan")
    evaluated = evaluate_department_queue_item_gateway_access(
        queue_item=item,
        evaluation_time=100,
    )

    assert evaluated["gateway_tool_name"] == "browser_search"
    assert evaluated["local_tool_id"] == "tool.google.search.v1"
    assert evaluated["gateway_evaluation"]["allowed"] is True
    assert evaluated["gateway_evaluation"]["tool_mode"] == "read_only_external"


def test_phase23o_live_publish_maps_to_approved_live_and_blocks_without_payload_approval():
    item = create_adapter_demo_item(department_id="marketing", capability="social.publish")
    evaluated = evaluate_department_queue_item_gateway_access(
        queue_item=item,
        evaluation_time=100,
    )

    assert evaluated["gateway_tool_name"] == "publish_facebook_post"
    assert evaluated["gateway_evaluation"]["allowed"] is False
    assert evaluated["gateway_evaluation"]["tool_mode"] == "approved_live_external"
    assert "missing_approved_payload_hash" in evaluated["gateway_evaluation"]["reasons"]
    assert "missing_approval_hash" in evaluated["gateway_evaluation"]["reasons"]


def test_phase23o_raw_model_tool_access_is_blocked_even_for_safe_gateway_capability():
    item = create_adapter_demo_item(department_id="builder", capability="document.create")
    evaluated = evaluate_department_queue_item_gateway_access(
        queue_item=item,
        evaluation_time=100,
        caller="model",
    )

    assert evaluated["gateway_evaluation"]["allowed"] is False
    assert "raw_model_tool_access_blocked" in evaluated["gateway_evaluation"]["reasons"]


def test_phase23o_unknown_department_capability_is_unsupported_not_executed():
    item = create_adapter_demo_item(department_id="builder", capability="unknown.random_tool")
    evaluated = evaluate_department_queue_item_gateway_access(
        queue_item=item,
        evaluation_time=100,
    )

    assert evaluated["adapted"] is False
    assert evaluated["adapter_state"] == "unsupported_department_capability"
    assert evaluated["gateway_evaluation"]["allowed"] is False
    assert evaluated["gateway_evaluation"]["reasons"] == ["unsupported_department_capability"]


def test_phase23o_department_capability_maps_are_explicit():
    assert gateway_capability_for_department_capability("campaign.plan") == "generate_copy"
    assert gateway_capability_for_department_capability("social.publish") == "publish_facebook_post"
    assert gateway_capability_for_department_capability("payment.create") == "take_payment"

    assert local_tool_id_for_department_capability("seo.plan") == "tool.google.search.v1"
    assert local_tool_id_for_department_capability("social.publish") == "tool.browser.computer_use.v1"
