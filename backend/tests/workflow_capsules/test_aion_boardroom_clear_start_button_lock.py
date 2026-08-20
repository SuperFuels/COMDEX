from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop" / "mac" / "src" / "app.js"


def app_text() -> str:
    return APP.read_text(encoding="utf-8")


def test_collapsed_boardroom_uses_an_explicit_start_meeting_button():
    text = app_text()
    assert 'data-aion-council-terminal-start="true"' in text
    assert "Start Board Meeting" in text
    assert "Boardroom context is ready" in text
    assert "press Enter to open board meeting" not in text


def test_start_button_runs_the_automatic_governed_board_meeting():
    text = app_text()
    start_handler = text.index(
        'const terminalStart = event.target?.closest?.("[data-aion-council-terminal-start=\'true\']")'
    )
    toggle_handler = text.index(
        'const terminalToggle = event.target?.closest?.("[data-aion-council-terminal-toggle=\'true\']")'
    )
    handler = text[start_handler:toggle_handler]
    assert 'runAionAutomaticBoardMeetingV1("business_assessment")' in handler


def test_expanded_terminal_exposes_only_session_and_meeting_controls():
    text = app_text()
    start = text.index("function renderBoardroomCouncilSessionTerminal()")
    end = text.index("/* AION PATCH: Safe Boardroom Council Terminal wrapper v1 */", start)
    renderer = text[start:end]

    assert 'data-aion-boardroom-meeting-controls="true"' in renderer
    assert "Restart Board Analysis" in renderer
    assert 'data-aion-council-session-add-context="true"' not in renderer
    assert 'data-aion-council-session-save="true"' not in renderer
    assert 'data-aion-council-session-ask-board="true"' not in renderer
    assert "Add Context" not in renderer
    assert "Save to Boardroom" not in renderer
    assert "Approve Pilot Plan" not in renderer


def test_automatic_meeting_runs_live_analysis_and_saves_internal_record():
    text = app_text()
    start = text.index("function runAionAutomaticBoardMeetingV1")
    end = text.index('window.aionRunAutomaticBoardMeetingV1 = runAionAutomaticBoardMeetingV1;', start)
    helper = text[start:end]

    assert "runAionLiveVisibleAskBoardResultV1(sessionType, runId)" in helper
    assert "commitAionBoardroomSessionArtifactPreview(sessionType)" in helper
    assert "External actions remain approval-gated" in text
