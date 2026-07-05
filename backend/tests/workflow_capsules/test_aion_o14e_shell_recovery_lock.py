from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o14e_shell_recovery_installed():
    assert "BEGIN AION O14E SHELL RECOVERY LOCK" in APP
    assert "recoverFromGoalSheetPilotTakeoverO14E" in APP
    assert "removeStuckGoalSheetPilotOverlaysO14E" in APP
    assert "restoreMainShellVisibilityO14E" in APP


def test_o14e_detects_stuck_goal_sheet_pilot_takeover_text():
    assert "Goal Sheet → Live Agents / Pilot" in APP
    assert "Preview task queue received" in APP
    assert "Marketing assignment received" in APP
    assert "startup_takeover_text_detected" in APP


def test_o14e_recovers_to_boardroom_shell():
    assert 'activeTab: "boardroom"' in APP
    assert 'boardroomViewMode: "spatial"' in APP
    assert "Recovered normal app shell from Goal Sheet preview takeover" in APP


def test_o14e_removes_stuck_o13d_overlays():
    assert "aion-o13d-live-agents-pilot-preview" in APP
    assert "data-aion-o13d-live-agents-pilot-preview" in APP
    assert "querySelectorAll(STUCK_OVERLAY_SELECTORS.join" in APP
