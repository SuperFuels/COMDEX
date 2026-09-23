from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RENDERER = ROOT / "desktop" / "mac" / "src" / "lib" / "desktop-boardroom-renderer.js"

def test_o15h3_snapshot_call_path_lock_installed():
    text = RENDERER.read_text(encoding="utf-8")
    assert "O15H.3 BOARD TEAM TABLE SNAPSHOT CALL PATH LOCK" in text
    assert "const boardSnapshotO15H3" in text
    assert "safeArray(boardSnapshotO15H3?.seats)" in text

def test_o15h3_board_team_call_path_is_snapshot_safe():
    text = RENDERER.read_text(encoding="utf-8")
    block_start = text.find("function addForcedVisibleBoardTeamSeats(parent, options = {})")
    block_end = text.find("function seatArc", block_start)
    block = text[block_start:block_end]
    assert "boardSnapshotO15H3" in block
    assert "options.snapshot" in block
    assert "safeArray(boardSnapshotO15H3?.seats)" in block

def test_o15h3_runtime_debug_available():
    text = RENDERER.read_text(encoding="utf-8")
    assert "global.__debugAionO15H3BoardTeamTableSnapshot" in text
    assert "usedFallback" in text
    assert "liveBoardSeatCount" in text
