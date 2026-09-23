from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop" / "mac" / "src" / "app.js"

def test_o15e_provider_rail_app_render_lock_installed():
    text = APP.read_text(encoding="utf-8")
    assert "O15E BOARDROOM PROVIDER RAIL APP RENDER LOCK" in text
    assert "window.__mountAionO15EBoardroomProviderRail" in text
    assert "window.__debugAionO15EProviderRail" in text
    assert "data-aion-o15e-boardroom-provider-rail" in text

def test_o15e_reads_boardroom_snapshot_seats():
    text = APP.read_text(encoding="utf-8")
    assert "getBoardroomSnapshot" in text
    assert "snapshot.seats" in text
    assert "seat.seat_type === \"connected_provider\"" in text
    assert "seat.connected === true" in text

def test_o15e_includes_gemini_and_does_not_fake_missing_providers():
    text = APP.read_text(encoding="utf-8")
    assert '"gemini"' in text
    assert '"claude"' in text
    assert '"grok"' in text
    assert "connected" in text
    assert "missing" not in text[text.find("BEGIN AION O15E"):text.find("END AION O15E")]
