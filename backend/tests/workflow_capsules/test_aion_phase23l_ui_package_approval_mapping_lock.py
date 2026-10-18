from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.local_node_router import router


APP_JS = Path("desktop/mac/src/app.js")
ROUTER = Path("backend/api/local_node_router.py")


def _client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_phase23l_frontend_sends_visible_work_package_steps_to_backend():
    text = APP_JS.read_text()

    assert "getAionPilotWorkPackageDraftStepsForBackend" in text
    assert "draft_steps: draftSteps" in text
    assert "approval_stages: approvalStages" in text
    assert "frontend_work_package_v0" in text


def test_phase23l_backend_uses_frontend_draft_steps_when_present():
    text = ROUTER.read_text()

    assert "frontend_draft_steps" in text
    assert "frontend_visible_work_package" in text
    assert "build_deterministic_mission_plan" in text


def test_phase23l_mission_preview_respects_ui_approval_pause():
    client = _client()

    response = client.post(
        "/api/local-node/aion/pilot/mission-preview",
        json={
            "business_id": "home-fixed",
            "mission_id": "phase23l_ui_package",
            "mission_run_id": "phase23l_ui_package_run",
            "user_goal": "produce a marketing plan for home fixed and execute the plan to grow the business",
            "template_id": "home_fixed_lead_campaign_v0",
            "draft_steps": [
                {"title": "Define marketing objective", "requires_approval": False},
                {"title": "Clarify target audience and offer", "requires_approval": False},
                {"title": "Draft positioning and core message", "requires_approval": True},
                {"title": "Build channel and content plan", "requires_approval": False},
                {"title": "Prepare lead capture workflow", "requires_approval": False},
                {"title": "Create review-ready marketing plan output", "requires_approval": False},
            ],
            "approval_stages": ["Draft positioning and core message"],
            "preview_only": True,
            "live_external_side_effects_enabled": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    steps = data["mission_plan"]["steps"]
    titles = [step["title"] for step in steps]

    assert titles == [
        "Define marketing objective",
        "Clarify target audience and offer",
        "Draft positioning and core message",
        "Build channel and content plan",
        "Prepare lead capture workflow",
        "Create review-ready marketing plan output",
    ]

    approval_step = steps[2]
    assert approval_step["decision"] == "checkpoint_required"
    assert approval_step["requires_checkpoint"] is True
    assert data["paused_step_id"] == approval_step["step_id"]

    assert "Approve public launch" not in titles
    assert all(step.get("action_type") != "publish_advert" for step in steps)
