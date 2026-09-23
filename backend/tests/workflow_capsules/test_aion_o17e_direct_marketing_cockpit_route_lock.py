from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_o17e_direct_route_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O17E DIRECT MARKETING COCKPIT ROUTE LOCK" in text
    assert "renderAionO17EMarketingPilotCockpit" in text
    assert "data-aion-o17e-marketing-pilot-cockpit" in text
    assert "data-aion-o17e-marketing-pilot-terminal" in text
    assert "Marketing Pilot Terminal · context packet" in text


def test_o17e_replaces_actual_surface_body_call():
    text = APP.read_text(encoding="utf-8")
    assert 'departmentKey === "marketing" && typeof renderAionO17EMarketingPilotCockpit === "function"' in text
    assert 'renderAionO17EMarketingPilotCockpit(selectedRuns, selectedAgentCard)' in text
    assert ': renderLiveAgentsWorkspaceBody(selectedRuns, selectedAgentCard)' in text


def test_o17e_keeps_spatial_mount_and_terminal_contract():
    text = APP.read_text(encoding="utf-8")
    assert "aionO17EMarketingSpatialBoardroomMount" in text
    assert "data-aion-o14d-department-121-spatial-boardroom-mount" in text
    assert 'data-aion-o14d-department-key="marketing"' in text
    assert "background:#0f172a" in text
    assert "color:#dbeafe" in text
    assert "box-shadow:inset 4px 0 0 #0284c7" in text
    assert "Marketing Context Packet" in text
    assert "Execution boundary: approval_gated" in text


def test_o17e_debug_exists():
    text = APP.read_text(encoding="utf-8")
    assert "__debugAionO17EMarketingPilotCockpit" in text
    assert "cockpit_exists" in text
    assert "terminal_exists" in text
    assert "spatial_mount_exists" in text
