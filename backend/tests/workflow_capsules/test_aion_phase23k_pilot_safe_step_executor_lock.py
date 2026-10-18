from pathlib import Path

import pytest

from backend.services.aion_mission_mode.pilot_safe_step_executor import (
    PilotSafeStepExecutionBlocked,
    execute_pilot_safe_step,
)


APP = Path("desktop/mac/src/app.js")
ROUTER = Path("backend/api/local_node_router.py")


def test_phase23k_executor_blocks_live_or_risky_action(tmp_path):
    with pytest.raises(PilotSafeStepExecutionBlocked):
        execute_pilot_safe_step(
            container_root=str(tmp_path),
            business_id="home-fixed",
            mission_id="m1",
            mission_run_id="r1",
            user_goal="publish it",
            step={
                "step_id": "s1",
                "title": "Publish advert",
                "action_type": "publish_facebook_post",
                "decision": "safe_internal",
            },
            assistant_fn=lambda prompt: "should not run",
        )


def test_phase23k_executor_generates_dynamic_output_and_artifact(tmp_path):
    result = execute_pilot_safe_step(
        container_root=str(tmp_path),
        business_id="home-fixed",
        mission_id="m1",
        mission_run_id="r1",
        user_goal="produce a marketing plan",
        step={
            "step_id": "s1",
            "title": "Create plan section",
            "action_type": "internal_planning",
            "decision": "safe_internal",
            "lane": "creation",
        },
        assistant_fn=lambda prompt: "DYNAMIC SAFE OUTPUT FROM PROVIDER",
    )

    assert result["status"] == "completed_draft_preview"
    assert result["output_text"] == "DYNAMIC SAFE OUTPUT FROM PROVIDER"
    assert result["live_external_side_effects_performed"] is False
    assert result["artifact_hash"].startswith("sha256:")
    assert result["receipt_hash"].startswith("sha256:")
    assert "business/home-fixed/missions/m1/runs/r1/artifacts/" in result["artifact_card"]["business_container_relative_path"]


def test_phase23k_backend_endpoint_exists():
    text = ROUTER.read_text()
    assert '@router.post("/aion/pilot/execute-safe-step")' in text
    assert "execute_pilot_safe_step" in text
    assert "live_external_side_effects_performed" in text


def test_phase23k_frontend_calls_execute_safe_step_not_fake_renderer():
    text = APP.read_text()

    assert "/execute-safe-step" in text
    assert "fetchAionPilotExecuteSafeStep" in text
    assert "executeAndAppendAionPilotMissionMapStepOutput" in text
    assert "function appendAionPilotMissionMapStepOutput" not in text
    assert "This fallback renderer is not allowed to manufacture task output." not in text

def test_phase23k_endpoint_bypasses_desktop_fact_shortcut():
    router = ROUTER.read_text()
    start = router.index('@router.post("/aion/pilot/execute-safe-step")')
    end = router.index('@router.post("/aion/pilot/mission-preview")', start)
    block = router[start:end]

    assert "ask_desktop_assistant" not in block
    assert "_call_selected_ai_provider" in block or "_call_ollama_chat" in block
