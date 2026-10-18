from backend.services.aion_mission_mode.business_function_router import route_business_function
from backend.services.aion_mission_mode.department_execution_queue import (
    add_blocked_live_action_cards,
    build_department_execution_queue,
    classify_capability_execution,
    create_department_queue_item,
)


def test_phase23n_queue_item_preserves_department_context():
    item = create_department_queue_item(
        business_id="home-fixed",
        mission_id="mission_001",
        mission_run_id="run_001",
        department_id="marketing",
        capability="campaign.plan",
        title="Marketing campaign plan",
        task_type="marketing_primary_work",
        task_index=0,
    )

    assert item["department_id"] == "marketing"
    assert item["department_display_name"] == "Marketing"
    assert item["capability"] == "campaign.plan"
    assert item["tool_mode"] == "safe_internal"
    assert item["status"] == "ready"
    assert item["queue_item_hash"].startswith("sha256:")


def test_phase23n_marketing_mission_builds_department_queues():
    queue = build_department_execution_queue(
        user_goal="Create a marketing campaign for Home Fixed with Facebook posts and adverts",
        business_id="home-fixed",
        mission_id="mission_marketing",
        mission_run_id="run_001",
    )

    assert queue["primary_department"] == "marketing"
    assert queue["supporting_departments"] == ["finance", "sales", "operations"]
    assert len(queue["department_queues"]["marketing"]) >= 8
    assert len(queue["department_queues"]["finance"]) >= 1
    assert len(queue["department_queues"]["sales"]) >= 1
    assert len(queue["department_queues"]["operations"]) >= 1
    assert queue["department_queue_hash"].startswith("sha256:")


def test_phase23n_builder_mission_stays_in_builder_queue():
    queue = build_department_execution_queue(
        user_goal="Build me a PDF quote template",
        business_id="home-fixed",
        mission_id="mission_builder",
        mission_run_id="run_001",
    )

    assert queue["primary_department"] == "builder"
    assert len(queue["department_queues"]["builder"]) >= 1
    assert all(item["department_id"] == "builder" for item in queue["department_queues"]["builder"])


def test_phase23n_staged_external_capabilities_are_staged_not_live():
    decision = classify_capability_execution("social.post_draft")

    assert decision["tool_mode"] == "staged_external"
    assert decision["status"] == "staged"
    assert decision["approval_required"] is False
    assert decision["live_external_side_effect"] is False


def test_phase23n_live_external_capabilities_wait_for_approval():
    decision = classify_capability_execution("social.publish")

    assert decision["tool_mode"] == "approved_live_external"
    assert decision["status"] == "waiting_approval"
    assert decision["approval_required"] is True
    assert decision["credential_required"] is True
    assert decision["live_external_side_effect"] is True


def test_phase23n_blocked_live_action_cards_are_not_executable():
    queue = build_department_execution_queue(
        user_goal="Create a marketing campaign for Home Fixed",
        business_id="home-fixed",
        mission_id="mission_live_blocked",
        mission_run_id="run_001",
    )

    with_live_cards = add_blocked_live_action_cards(queue=queue)

    live_items = [item for item in with_live_cards["queue_items"] if item["status"] == "waiting_approval"]

    assert live_items
    assert all(item["approval_required"] is True for item in live_items)
    assert all(item["live_external_side_effect"] is True for item in live_items)


def test_phase23n_queue_hash_is_deterministic():
    a = build_department_execution_queue(
        user_goal="Create a marketing campaign for Home Fixed",
        business_id="home-fixed",
        mission_id="mission_hash",
        mission_run_id="run_001",
    )
    b = build_department_execution_queue(
        user_goal="Create a marketing campaign for Home Fixed",
        business_id="home-fixed",
        mission_id="mission_hash",
        mission_run_id="run_001",
    )

    assert a["department_queue_hash"] == b["department_queue_hash"]


def test_phase23n_accepts_precomputed_route():
    route = route_business_function(
        user_goal="Create a finance forecast",
        business_id="home-fixed",
        mission_id="mission_route",
        mission_run_id="run_001",
    )

    queue = build_department_execution_queue(
        user_goal="Create a finance forecast",
        business_id="home-fixed",
        mission_id="mission_route",
        mission_run_id="run_001",
        routed_plan=route,
    )

    assert queue["primary_department"] == "finance"
    assert queue["department_queues"]["finance"]
