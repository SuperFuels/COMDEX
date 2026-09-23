from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RENDERER = ROOT / "desktop" / "mac" / "src" / "lib" / "desktop-boardroom-renderer.js"

def test_o15f_real_3d_provider_seats_lock_installed():
    text = RENDERER.read_text(encoding="utf-8")
    assert "O15F REAL 3D BOARDROOM PROVIDER SEATS LOCK" in text
    assert "O15F BOARD MODE SNAPSHOT SEATS ONLY LOCK" in text
    assert "sourceBoardSeatsO15F" in text
    assert "boardSeatsFromSnapshotO15F" in text

def test_o15f_3d_table_reads_snapshot_seats():
    text = RENDERER.read_text(encoding="utf-8")
    assert "safeArray(snapshot?.seats)" in text
    assert '"connected_provider"' in text
    assert 'seat.connected === true' in text
    assert 'status === "connected"' in text
    assert 'status === "always_on"' in text

def test_o15f_removed_old_hardcoded_fake_board_team():
    text = RENDERER.read_text(encoding="utf-8")
    assert '["openai", "OpenAI", "Model Provider", 5.6, -8.7, 0x22c55e]' not in text
    assert '["claude", "Claude", "External LLM"]' not in text
    assert '["grok", "Grok", "External LLM"]' not in text
    assert '["gemini", "Gemini", "External LLM"]' not in text
