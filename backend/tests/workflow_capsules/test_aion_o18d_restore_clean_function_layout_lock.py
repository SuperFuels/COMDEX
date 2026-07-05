from pathlib import Path

APP = Path("desktop/mac/src/app.js")
RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js")

def test_o18d_layout_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18D RESTORE CLEAN FUNCTION COCKPIT LAYOUT" in text
    assert "aion-o18d-restore-clean-function-cockpit-layout" in text
    assert "__debugAionO18DRestoreCleanFunctionCockpitLayout" in text
    assert 'grid-template-areas:' in text
    assert '"header agent"' in text
    assert '"terminal agent"' in text

def test_o18d_retracts_broken_absolute_layout():
    text = APP.read_text(encoding="utf-8")
    assert "position:relative !important" in text
    assert "top:auto !important" in text
    assert "right:auto !important" in text
    assert "padding-right:14px !important" in text
    assert '[data-aion-o18b-agent-figure="true"]' in text
    assert "display:none !important" in text

def test_o18d_safe_camera_values():
    text = RENDERER.read_text(encoding="utf-8")
    assert "BEGIN AION O18D REAL AGENT SAFE PORTRAIT CAMERA LOCK" in text
    assert "radius: 8.2" in text
    assert "phi: 0.038" in text
    assert "y: 2.85" in text
    assert "targetY: 1.65" in text
    assert "targetZ: -8.15" in text
