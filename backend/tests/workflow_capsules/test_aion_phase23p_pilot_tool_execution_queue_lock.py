from backend.services.aion_mission_mode.department_execution_queue import (
    build_department_execution_queue,
    create_department_queue_item,
)
from backend.services.aion_mission_mode.pilot_tool_execution_queue import (
    build_pilot_tool_execution_queue,
    create_tool_execution_item,
    next_runnable_tool_item,
    summarize_tool_execution_queue,
)


def test_phase23p_safe_internal_department_item_becomes_ready_tool_item():
    queue_item = create_department_queue_item(
        business_id="home-fixed",
        mission_id="mission_tool",
        mission_run_id="run_001",
        department_id="marketing",
        capability="campaign.plan",
        title="Campaign plan",
        task_type="marketing_primary_work",
        task_index=0,
    )

    tool_item = create_tool_execution_item(
        queue_item=queue_item,
        evaluation_time=100,
    )

    assert tool_item["department_id"] == "marketing"
    assert tool_item["department_capability"] == "campaign.plan"
    assert tool_item["gateway_tool_name"] == "generate_copy"
    assert tool_item["tool_mode"] == "safe_internal"
    assert tool_item["status"] == "ready"
    assert tool_item["execution_allowed"] is True
    assert tool_item["live_execution_allowed"] is False


def test_phase23p_staged_external_item_becomes_staged_not_live():
    queue_item = create_department_queue_item(
        business_id="home-fixed",
        mission_id="mission_tool",
        mission_run_id="run_001",
        department_id="marketing",
        capability="social.post_draft",
        title="Facebook post draft",
        task_type="marketing_primary_work",
        task_index=1,
    )

    tool_item = create_tool_execution_item(
        queue_item=queue_item,
        evaluation_time=100,
    )

    assert tool_item["gateway_tool_name"] == "prepare_facebook_post"
    assert tool_item["tool_mode"] == "staged_external"
    assert tool_item["status"] == "staged"
    assert tool_item["execution_allowed"] is True
    assert tool_item["live_external_side_effect"] is False


def test_phase23p_live_external_item_waits_for_approval():
    queue_item = create_department_queue_item(
        business_id="home-fixed",
        mission_id="mission_tool",
        mission_run_id="run_001",
        department_id="marketing",
        capability="social.publish",
        title="Publish Facebook post",
        task_type="blocked_live_action",
        task_index=0,
    )

    tool_item = create_tool_execution_item(
        queue_item=queue_item,
        evaluation_time=100,
    )

    assert tool_item["gateway_tool_name"] == "publish_facebook_post"
    assert tool_item["tool_mode"] == "approved_live_external"
    assert tool_item["status"] == "waiting_approval"
    assert tool_item["execution_allowed"] is False
    assert tool_item["approval_required"] is True
    assert tool_item["credential_required"] is True
    assert tool_item["live_external_side_effect"] is True


def test_phase23p_raw_model_caller_is_blocked():
    queue_item = create_department_queue_item(
        business_id="home-fixed",
        mission_id="mission_tool",
        mission_run_id="run_001",
        department_id="builder",
        capability="document.create",
        title="Builder document",
        task_type="builder_work",
        task_index=0,
    )

    tool_item = create_tool_execution_item(
        queue_item=queue_item,
        evaluation_time=100,
        caller="model",
    )

    assert tool_item["gateway_allowed"] is False
    assert tool_item["status"] == "blocked"
    assert "raw_model_tool_access_blocked" in tool_item["gateway_reasons"]


def test_phase23p_builds_tool_queue_from_department_queue():
    department_queue = build_department_execution_queue(
        user_goal="Create a marketing campaign for Home Fixed",
        business_id="home-fixed",
        mission_id="mission_queue",
        mission_run_id="run_001",
    )

    tool_queue = build_pilot_tool_execution_queue(
        user_goal="Create a marketing campaign for Home Fixed",
        business_id="home-fixed",
        mission_id="mission_queue",
        mission_run_id="run_001",
        department_queue=department_queue,
        evaluation_time=100,
    )

    assert tool_queue["primary_department"] == "marketing"
    assert tool_queue["tool_execution_items"]
    assert tool_queue["department_tool_queues"]["marketing"]
    assert tool_queue["ready_count"] >= 1
    assert tool_queue["staged_count"] >= 1
    assert tool_queue["live_execution_allowed"] is False
    assert tool_queue["raw_model_tool_access_allowed"] is False
    assert tool_queue["tool_queue_hash"].startswith("sha256:")


def test_phase23p_blocked_live_actions_are_present_but_not_executable():
    tool_queue = build_pilot_tool_execution_queue(
        user_goal="Create a marketing campaign for Home Fixed",
        business_id="home-fixed",
        mission_id="mission_live",
        mission_run_id="run_001",
        include_blocked_live_actions=True,
        evaluation_time=100,
    )

    live_items = [
        item
        for item in tool_queue["tool_execution_items"]
        if item["status"] == "waiting_approval"
    ]

    assert live_items
    assert all(item["execution_allowed"] is False for item in live_items)
    assert all(item["live_external_side_effect"] is True for item in live_items)


def test_phase23p_next_runnable_tool_item_returns_safe_or_staged_item():
    tool_queue = build_pilot_tool_execution_queue(
        user_goal="Create a marketing campaign for Home Fixed",
        business_id="home-fixed",
        mission_id="mission_next",
        mission_run_id="run_001",
        include_blocked_live_actions=True,
        evaluation_time=100,
    )

    item = next_runnable_tool_item(tool_queue)

    assert item is not None
    assert item["status"] in {"ready", "staged"}
    assert item["execution_allowed"] is True
    assert item["live_execution_allowed"] is False


def test_phase23p_tool_queue_hash_and_summary_are_deterministic():
    a = build_pilot_tool_execution_queue(
        user_goal="Create a marketing campaign for Home Fixed",
        business_id="home-fixed",
        mission_id="mission_hash",
        mission_run_id="run_001",
        evaluation_time=100,
    )
    b = build_pilot_tool_execution_queue(
        user_goal="Create a marketing campaign for Home Fixed",
        business_id="home-fixed",
        mission_id="mission_hash",
        mission_run_id="run_001",
        evaluation_time=100,
    )

    assert a["tool_queue_hash"] == b["tool_queue_hash"]

    sa = summarize_tool_execution_queue(a)
    sb = summarize_tool_execution_queue(b)

    assert sa["summary_hash"] == sb["summary_hash"]
    assert sa["live_execution_allowed"] is False
    assert sa["raw_model_tool_access_allowed"] is False
