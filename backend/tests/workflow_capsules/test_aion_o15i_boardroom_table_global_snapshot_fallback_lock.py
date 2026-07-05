from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RENDERER = ROOT / "desktop" / "mac" / "src" / "lib" / "desktop-boardroom-renderer.js"

def test_o15i_global_snapshot_fallback_installed():
    text = RENDERER.read_text(encoding="utf-8")
    assert "O15I BOARD TEAM GLOBAL SNAPSHOT FALLBACK LOCK" in text
    assert "global.getBoardroomSnapshot" in text
    assert "globalBoardSnapshotO15I" in text
    assert "safeArray(globalBoardSnapshotO15I?.seats).length" in text

def test_o15i_prefers_non_empty_snapshot_sources():
    text = RENDERER.read_text(encoding="utf-8")
    block_start = text.find("BEGIN AION O15I")
    block_end = text.find("END AION O15I", block_start)
    block = text[block_start:block_end]
    assert "localOptionSnapshotO15I" in block
    assert "localRenderSnapshotO15I" in block
    assert "boardSnapshotO15H3" in block
    assert "safeArray(localOptionSnapshotO15I?.seats).length" in block
    assert "safeArray(localRenderSnapshotO15I?.seats).length" in block

def test_o15i_debug_reports_snapshot_sources():
    text = RENDERER.read_text(encoding="utf-8")
    assert "globalSnapshotSeatCount" in text
    assert "optionSnapshotSeatCount" in text
    assert "renderSnapshotSeatCount" in text
