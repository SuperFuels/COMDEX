from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    assert "BEGIN AION O13D LIVE AGENTS PILOT PREVIEW STATE BRIDGE" in APP_JS
    return APP_JS.split("BEGIN AION O13D LIVE AGENTS PILOT PREVIEW STATE BRIDGE", 1)[1].split(
        "END AION O13D LIVE AGENTS PILOT PREVIEW STATE BRIDGE", 1
    )[0]


def test_o13d_installed():
    b = block()
    assert "Live Agents / Pilot preview state bridge installed" in b
    assert "aionBuildPilotPreviewStateO13D" in b
    assert "aionPublishPilotPreviewStateO13D" in b


def test_o13d_builds_central_pilot_preview_queue():
    b = block()
    assert "central_pilot" in b
    assert "existing_central_pilot_reused: true" in b
    assert "window.__aionExistingCentralPilotPreviewQueue" in b
    assert "coordinator_guarded_executor" in b


def test_o13d_builds_department_pilot_preview_queues():
    b = block()
    assert "departmentStates" in b
    assert "window.__aionExistingDepartmentPilotPreviewQueues" in b
    assert "receiving_goal_sheet_preview_tasks" in b
    assert "live_agents.${department}" in b


def test_o13d_supports_all_five_departments():
    b = block()
    for department in ["marketing", "sales", "finance", "operations", "support"]:
        assert f'"{department}"' in b


def test_o13d_preview_state_never_executes():
    b = block()
    assert "preview_only: true" in b
    assert "approval_required: true" in b
    assert "execution_allowed_now: false" in b
    assert "connector_call_required: false" in b
    assert "external_side_effects: false" in b
    assert "no_live_agent_execution: true" in b
    assert "no_customer_messages: true" in b


def test_o13d_wraps_o13c_packet_builders():
    b = block()
    assert "aionBuildAllDepartmentPilotTaskPacketsO13C" in b
    assert "aionBuildActiveDepartmentPilotTaskPacketsO13C" in b
    assert "__aionO13DWrapped" in b
    assert "renderPilotPreviewPanelO13D(state)" in b


def test_o13d_exposes_preview_panel_and_state_hooks():
    b = block()
    assert "aion-o13d-live-agents-pilot-preview" in b
    assert "Preview task queue received" in b
    assert "window.aionRenderPilotPreviewPanelO13D" in b
    assert "window.aionClosePilotPreviewPanelO13D" in b


def test_o13d_dispatches_preview_state_event():
    b = block()
    assert "aion:goal-sheet-pilot-preview-state" in b
    assert "CustomEvent" in b
    assert "document.dispatchEvent" in b
    assert "window.dispatchEvent" in b
