from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RENDERER = ROOT / "desktop" / "mac" / "src" / "lib" / "desktop-boardroom-renderer.js"

def test_o15d_provider_visibility_lock_installed():
    text = RENDERER.read_text(encoding="utf-8")
    assert "O15D BOARDROOM CONNECTED PROVIDER VISIBILITY LOCK" in text
    assert "aion-o15d-provider-seat" in text
    assert "data-aion-o15d-provider-seat" in text
    assert "window.__debugAionO15DProviderRail" in text

def test_o15d_uses_snapshot_seats_and_connected_provider_type():
    text = RENDERER.read_text(encoding="utf-8")
    assert "snapshot.seats" in text
    assert 'seat.seat_type === "connected_provider"' in text
    assert "seat.connected === true" in text
    assert "Gemini" not in text or "connected_provider" in text

def test_o15d_wraps_mount_and_update_boardroom():
    text = RENDERER.read_text(encoding="utf-8")
    assert "renderer.mountBoardroom = function mountBoardroomWithProviderRailO15D" in text
    assert "renderer.updateBoardroom = function updateBoardroomWithProviderRailO15D" in text
    assert "renderProviderRail(rendererState)" in text
