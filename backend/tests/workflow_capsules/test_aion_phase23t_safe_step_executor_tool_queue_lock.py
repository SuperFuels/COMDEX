from pathlib import Path

import pytest

from backend.services.aion_mission_mode.department_execution_queue import create_department_queue_item
from backend.services.aion_mission_mode.pilot_safe_step_executor import (
    PilotSafeStepExecutionBlocked,
    execute_pilot_safe_step,
)
from backend.services.aion_mission_mode.pilot_tool_execution_queue import create_tool_execution_item


def make_tool_item(*, capability: str, department_id: str = "marketing", evaluation_time: int = 100):
    queue_item = create_department_queue_item(
        business_id="home-fixed",
        mission_id="mission_23t",
        mission_run_id="run_001",
        department_id=department_id,
        capability=capability,
        title=f"{department_id}: {capability}",
        task_type=f"{department_id}_work",
        task_index=0,
    )
    return create_tool_execution_item(
        queue_item=queue_item,
        evaluation_time=evaluation_time,
    )


def test_phase23t_safe_internal_tool_item_generates_draft_artifact(tmp_path):
    tool_item = make_tool_item(capability="campaign.plan")

    result = execute_pilot_safe_step(
        container_root=str(tmp_path),
        business_id="home-fixed",
        mission_id="mission_23t",
        mission_run_id="run_001",
        user_goal="Create a marketing campaign",
        step={},
        step_index=0,
        tool_execution_item=tool_item,
        assistant_fn=lambda prompt: "Campaign plan draft from governed queue item.",
    )

    assert result["status"] == "completed_draft_preview"
    assert result["tool_queue_bound"] is True
    assert result["department_id"] == "marketing"
    assert result["department_capability"] == "campaign.plan"
    assert result["gateway_tool_name"] == "generate_copy"
    assert result["tool_mode"] == "safe_internal"
    assert result["live_external_side_effects_performed"] is False
    assert result["raw_tool_execution_allowed"] is False
    assert result["artifact_hash"].startswith("sha256:")
    assert result["receipt_hash"].startswith("sha256:")


def test_phase23t_staged_external_tool_item_generates_reviewable_draft_only(tmp_path):
    tool_item = make_tool_item(capability="social.post_draft")

    result = execute_pilot_safe_step(
        container_root=str(tmp_path),
        business_id="home-fixed",
        mission_id="mission_23t",
        mission_run_id="run_001",
        user_goal="Create a Facebook post",
        step={},
        step_index=0,
        tool_execution_item=tool_item,
        assistant_fn=lambda prompt: "Facebook post draft for review.",
    )

    assert result["status"] == "completed_draft_preview"
    assert result["tool_mode"] == "staged_external"
    assert result["department_capability"] == "social.post_draft"
    assert result["live_external_side_effects_performed"] is False
    assert result["raw_tool_execution_allowed"] is False


def test_phase23t_live_tool_item_is_blocked_before_generation(tmp_path):
    tool_item = make_tool_item(capability="social.publish")

    with pytest.raises(PilotSafeStepExecutionBlocked) as exc:
        execute_pilot_safe_step(
            container_root=str(tmp_path),
            business_id="home-fixed",
            mission_id="mission_23t",
            mission_run_id="run_001",
            user_goal="Publish a Facebook post",
            step={},
            step_index=0,
            tool_execution_item=tool_item,
            assistant_fn=lambda prompt: "This should not run.",
        )

    assert "tool_item_status_not_runnable:waiting_approval" in str(exc.value)
    assert "tool_mode_not_safe_for_step_executor:approved_live_external" in str(exc.value)


def test_phase23t_blocked_model_access_tool_item_is_blocked(tmp_path):
    queue_item = create_department_queue_item(
        business_id="home-fixed",
        mission_id="mission_23t",
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

    with pytest.raises(PilotSafeStepExecutionBlocked) as exc:
        execute_pilot_safe_step(
            container_root=str(tmp_path),
            business_id="home-fixed",
            mission_id="mission_23t",
            mission_run_id="run_001",
            user_goal="Create a document",
            step={},
            step_index=0,
            tool_execution_item=tool_item,
            assistant_fn=lambda prompt: "This should not run.",
        )

    assert "tool_item_status_not_runnable:blocked" in str(exc.value)
    assert "tool_execution_not_allowed_by_gateway" in str(exc.value)


def test_phase23t_route_passes_tool_execution_item_to_executor():
    route_text = Path("backend/api/local_node_router.py").read_text()

    assert "tool_execution_item = body.get" in route_text
    assert "tool_execution_item=tool_execution_item" in route_text
