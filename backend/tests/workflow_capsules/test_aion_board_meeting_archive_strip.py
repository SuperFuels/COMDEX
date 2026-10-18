from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
STYLES = (ROOT / "desktop/mac/src/styles.css").read_text(encoding="utf-8")


def test_boardroom_renders_slim_meeting_archive_before_terminal_header():
    terminal = APP[APP.index("function renderBoardroomCouncilSessionTerminal"):APP.index("/* AION PATCH: Safe Boardroom Council Terminal")]
    assert "${renderAionBoardMeetingArchiveStripV1()}" in terminal
    assert terminal.index("${renderAionBoardMeetingArchiveStripV1()}") < terminal.index("Boardroom Terminal · context packet")
    assert 'data-aion-board-meeting-archive="true"' in APP
    assert "Latest" in APP
    assert "Open minutes" in APP


def test_archive_reuses_file_cabinet_records_and_reader():
    archive = APP[APP.index("function getAionBoardMeetingArchiveEntriesV1"):APP.index("function buildAionBoardroomSessionPacket")]
    assert "readAionBoardroomSessionArtifacts()" in archive
    assert "getAionFileCabinetTree()" in archive
    assert "boardroom_session_pointer_" in archive
    assert "window.__aionOpenFileCabinetArtifactV1(itemId, entry.node)" in archive
    assert 'window.setAionSidebarActiveTabHardV1("file_cabinet")' in archive


def test_archive_is_expandable_and_compact():
    assert 'data-aion-board-meeting-archive-toggle="true"' in APP
    assert "window.__aionBoardMeetingArchiveExpandedV1" in APP
    assert ".aion-board-meeting-archive-summary" in STYLES
    assert "min-height: 54px;" in STYLES
