from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    assert "BEGIN AION O13E LIVE AGENTS WORKSPACE GOAL SHEET QUEUE INJECTION" in APP_JS
    return APP_JS.split("BEGIN AION O13E LIVE AGENTS WORKSPACE GOAL SHEET QUEUE INJECTION", 1)[1].split(
        "END AION O13E LIVE AGENTS WORKSPACE GOAL SHEET QUEUE INJECTION", 1
    )[0]


def test_o13e_installed():
    b = block()
    assert "Live Agents workspace Goal Sheet queue injection installed" in b
    assert "aionRenderLiveAgentsGoalSheetPilotQueuePanelO13E" in b
    assert "aionWrapLiveAgentsWorkspaceBodyO13E" in b


def test_o13e_wraps_actual_live_agents_workspace_body():
    b = block()
    assert "renderLiveAgentsWorkspaceBody" in b
    assert "renderLiveAgentsWorkspaceBodyWithGoalSheetQueue" in b
    assert "__aionO13EWrapped" in b
    assert "return `${queueHtml}${originalHtml}`" in b


def test_o13e_renders_goal_sheet_queue_inside_live_agents():
    b = block()
    assert "renderLiveAgentsGoalSheetPilotQueuePanelO13E" in b
    assert "data-aion-o13e-live-agents-goal-sheet-queue" in b
    assert "Goal Sheet → Existing Live Agents / Pilot" in b
    assert "Real preview packets from Department Goal Sheets" in b


def test_o13e_central_and_department_pilot_queues_visible():
    b = block()
    assert "Central Pilot queue" in b
    assert "Department Pilot queues" in b
    assert "Marketing Pilot" in b or "DEPARTMENT_LABELS" in b
    assert "data-aion-o13e-live-agent-department" in b


def test_o13e_supports_opening_department_pilot_from_queue():
    b = block()
    assert "openDepartmentPilotFromQueueO13E" in b
    assert "setLiveAgentsWorkspace" in b
    assert "window.__aionPreferredLiveAgentDepartment" in b
    assert "data-aion-o13e-open-department-pilot" in b


def test_o13e_uses_o13d_preview_state_not_dummy_data():
    b = block()
    assert "aionPublishPilotPreviewStateO13D" in b
    assert "__aionGoalLoopPilotQueuePreview" in b
    assert "__aionGoalSheetPilotTaskQueueO13C" in b
    assert "__aionCentralPilotGoalSheetTaskQueuePreview" in b


def test_o13e_no_execution_or_connector_actions():
    b = block()
    assert "No execution, no connector calls, no persistence, no customer actions" in b
    assert "execution_allowed_now" in b
    assert "connector_call_required" in b
    assert "external_side_effects" in b
    assert "0</strong><span>Executed" in b


def test_o13e_is_not_a_floating_overlay():
    b = block()
    assert "position: fixed" not in b
    assert "appendChild(shell)" not in b
    assert "return `${queueHtml}${originalHtml}`" in b
