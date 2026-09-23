from backend.services.aion_mission_mode.business_function_router import route_business_function
from backend.services.aion_mission_mode.department_execution_queue import (
    add_blocked_live_action_cards,
    build_department_execution_queue,
)
from backend.services.aion_mission_mode.department_artifact_persistence import (
    commit_department_artifact_from_pilot_result,
)
from backend.services.aion_mission_mode.marketing_department_pack import (
    create_home_fixed_marketing_fixture_pack,
)
from backend.services.aion_mission_mode.pilot_safe_step_executor import execute_pilot_safe_step
from backend.services.aion_mission_mode.pilot_tool_approval_cards import (
    create_exact_payload_approval_card,
)
from backend.services.aion_mission_mode.pilot_tool_execution_queue import (
    build_pilot_tool_execution_queue,
    next_runnable_tool_item,
)


HOME_FIXED_GOAL = (
    "Create a Home Fixed marketing campaign for Facebook posts, adverts, lead capture, "
    "sales follow-up and fulfilment readiness across Almería and Murcia."
)


def test_phase23w_home_fixed_routes_to_marketing_with_support_departments():
    route = route_business_function(
        user_goal=HOME_FIXED_GOAL,
        business_id="home-fixed",
        mission_id="home_fixed_phase23w_smoke",
        mission_run_id="run_001",
    )

    assert route["primary_department"] == "marketing"
    assert "finance" in route["supporting_departments"]
    assert "sales" in route["supporting_departments"]
    assert "operations" in route["supporting_departments"]
    assert route["department_route_hash"].startswith("sha256:")


def test_phase23w_home_fixed_pack_contains_queues_and_no_live_execution():
    pack = create_home_fixed_marketing_fixture_pack(
        mission_id="home_fixed_phase23w_smoke",
        mission_run_id="run_001",
    )

    assert pack["primary_department"] == "marketing"
    assert pack["department_queue"]["primary_department"] == "marketing"
    assert pack["tool_execution_queue"]["primary_department"] == "marketing"
    assert pack["tool_execution_queue"]["ready_count"] >= 1
    assert pack["tool_execution_queue"]["staged_count"] >= 1
    assert pack["tool_execution_queue"]["waiting_approval_count"] >= 1
    assert pack["tool_execution_queue"]["live_execution_allowed"] is False
    assert pack["tool_execution_queue"]["raw_model_tool_access_allowed"] is False


def test_phase23w_home_fixed_safe_item_generates_department_bound_artifact(tmp_path):
    department_queue = build_department_execution_queue(
        user_goal=HOME_FIXED_GOAL,
        business_id="home-fixed",
        mission_id="home_fixed_phase23w_smoke",
        mission_run_id="run_001",
    )
    tool_queue = build_pilot_tool_execution_queue(
        user_goal=HOME_FIXED_GOAL,
        business_id="home-fixed",
        mission_id="home_fixed_phase23w_smoke",
        mission_run_id="run_001",
        department_queue=department_queue,
        evaluation_time=100,
    )

    tool_item = next_runnable_tool_item(tool_queue)

    assert tool_item is not None
    assert tool_item["status"] in {"ready", "staged"}
    assert tool_item["execution_allowed"] is True
    assert tool_item["live_execution_allowed"] is False

    pilot_result = execute_pilot_safe_step(
        container_root=str(tmp_path),
        business_id="home-fixed",
        mission_id="home_fixed_phase23w_smoke",
        mission_run_id="run_001",
        user_goal=HOME_FIXED_GOAL,
        step={},
        step_index=0,
        tool_execution_item=tool_item,
        assistant_fn=lambda prompt: "Home Fixed campaign draft for review. No live publishing performed.",
    )

    record = commit_department_artifact_from_pilot_result(
        pilot_result=pilot_result,
        tool_execution_item=tool_item,
    )

    assert pilot_result["live_external_side_effects_performed"] is False
    assert pilot_result["raw_tool_execution_allowed"] is False
    assert record["target"]["business_container_id"] == "home-fixed"
    assert record["target"]["sub_container"] in {
        "marketing",
        "finance",
        "sales",
        "operations",
        "support",
        "builder",
        "pilot",
    }
    assert record["storage_path"].startswith(
        f"business_containers/home-fixed/{record['target']['sub_container']}/"
    )
    assert record["record_valid"] is True
    assert record["merkle_triad_valid"] is True
    assert record["replay_locator"]["mission_id"] == "home_fixed_phase23w_smoke"
    assert record["replay_locator_hash"].startswith("sha256:")


def test_phase23w_home_fixed_live_actions_remain_approval_cards_only():
    department_queue = build_department_execution_queue(
        user_goal=HOME_FIXED_GOAL,
        business_id="home-fixed",
        mission_id="home_fixed_phase23w_smoke",
        mission_run_id="run_001",
    )
    guarded_queue = add_blocked_live_action_cards(queue=department_queue)

    tool_queue = build_pilot_tool_execution_queue(
        user_goal=HOME_FIXED_GOAL,
        business_id="home-fixed",
        mission_id="home_fixed_phase23w_smoke",
        mission_run_id="run_001",
        department_queue=guarded_queue,
        evaluation_time=100,
    )

    waiting_live_items = [
        item
        for item in tool_queue["tool_execution_items"]
        if item["status"] == "waiting_approval"
        and item["tool_mode"] == "approved_live_external"
    ]

    assert waiting_live_items

    card = create_exact_payload_approval_card(
        tool_execution_item=waiting_live_items[0],
        approval_expires_at=200,
    )

    assert card["approval_state"] == "waiting_exact_payload_approval"
    assert card["live_execution_allowed"] is False
    assert card["external_side_effect_executed"] is False
    assert tool_queue["live_execution_allowed"] is False
    assert tool_queue["raw_model_tool_access_allowed"] is False


def test_phase23w_smoke_contract_has_no_live_side_effects():
    pack = create_home_fixed_marketing_fixture_pack(
        mission_id="home_fixed_phase23w_smoke",
        mission_run_id="run_001",
    )

    queue = pack["tool_execution_queue"]

    assert queue["live_execution_allowed"] is False
    assert queue["raw_model_tool_access_allowed"] is False

    for item in queue["tool_execution_items"]:
        assert item["live_execution_allowed"] is False
        assert item.get("external_side_effect_executed") in {None, False}
        assert item.get("raw_model_tool_access_allowed") in {None, False}
