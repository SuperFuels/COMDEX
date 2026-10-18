from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RENDERER = ROOT / "desktop" / "mac" / "src" / "lib" / "desktop-boardroom-renderer.js"

def test_o15g_snapshot_executive_bots_lock_installed():
    text = RENDERER.read_text(encoding="utf-8")
    assert "O15G SNAPSHOT EXECUTIVE BOTS LOCK" in text
    assert "function buildExecutiveBots(parent, snapshot = {})" in text
    assert "safeArray(snapshot?.seats)" in text

def test_o15g_removed_old_three_bot_hardcode():
    text = RENDERER.read_text(encoding="utf-8")
    assert 'const ceo = buildHexFloor("CEO"' not in text
    assert 'const aion = buildHexFloor("AION"' not in text
    assert 'const openai = buildHexFloor("OpenAI"' not in text
    assert "function buildExecutiveBots(parent, snapshot = {})" in text

def test_o15g_does_not_fake_missing_connected_providers():
    text = RENDERER.read_text(encoding="utf-8")
    block = text[text.find("BEGIN AION O15G"):text.find("END AION O15G")]
    assert 'seatType === "connected_provider"' in block
    assert 'seat.connected === true' in block
    assert 'status === "connected"' in block
    assert 'if (!alwaysOn && !connected) return null' in block
