from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase21l_lock_marker_exists():
    assert "PHASE 21L LOCK: Live Agents Aion Pilot cockpit mount" in TEXT
    assert "data-aion-phase21l-live-agents-aion-pilot-mount" in TEXT


def test_phase21l_aion_or_pilot_department_routes_to_aion_workspace_surface():
    start = TEXT.index("function renderLiveAgentsWorkspaceBody(selectedRuns, selectedAgentCard)")
    end = TEXT.index("function renderLiveAgentRunRow", start)
    block = TEXT[start:end]

    assert 'if (departmentKey === "aion")' in block
    assert 'if (departmentKey === "pilot")' in block
    assert block.count("return renderAionWorkspaceSurface(selectedRuns, scopedSelectedAgentCard);") >= 2

def test_phase21l_mounts_inside_confirmed_aion_workspace_surface():
    start = TEXT.index("function renderAionWorkspaceSurface(selectedRuns, selectedAgentCard)")
    end = TEXT.index("function getDepartmentRecentAudit", start)
    block = TEXT[start:end]

    assert "installAionPilotCockpitStyles();" in block
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in block
    assert "data-aion-phase21l-live-agents-aion-pilot-mount" in block
    assert "renderAionGoalLoopFounderDemoTracePanel" not in block


def test_phase21l_operator_identity_is_carried_by_runtime_not_page_chrome():
    assert "AION Pilot native runtime executor, not UI automation" in TEXT
    assert "No money, post, deploy, external send" in TEXT


def test_phase21l_top_level_aion_chat_points_to_live_agents_aion():
    assert "data-aion-pilot-chat-pointer" in TEXT
    assert "Live Agents → Aion" in TEXT


def test_phase21l_no_duplicate_full_cockpit_inside_top_level_aion_chat():
    start = TEXT.index("function renderAionChatSurface()")
    end = TEXT.index("function renderAionToolMiniCard", start)
    block = TEXT[start:end]
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" not in block


def test_phase21l_pilot_renderer_still_exists():
    assert "function renderAionPilotCockpitPanel" in TEXT
    assert "function getAionPilotCockpitSnapshot" in TEXT


def test_phase21l_safety_message_remains_visible():
    assert "AION stopped itself before doing anything risky." in TEXT
    assert "No money, post, deploy, external send, booking, escrow or reputation mutation without exact approval." in TEXT


def test_phase21l_no_live_external_buttons_by_default():
    forbidden = [
        "data-aion-pilot-live-pay",
        "data-aion-pilot-live-deploy",
        "data-aion-pilot-live-send",
        "data-aion-pilot-live-post",
        "data-aion-pilot-live-book",
        "data-aion-pilot-live-escrow",
    ]
    for token in forbidden:
        assert token not in TEXT


def test_phase21l_pdf_request_still_visible():
    assert "Build me a PDF document with X data" in TEXT
