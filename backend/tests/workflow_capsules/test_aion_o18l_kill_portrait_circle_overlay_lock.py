from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o18l_circle_overlay_kill_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18L KILL PORTRAIT CIRCLE OVERLAY FINAL LOCK" in text
    assert "aion-o18l-kill-portrait-circle-overlay-final-style" in text
    assert "__debugAionO18LKillPortraitCircleOverlay" in text
    assert "background-image:none !important" in text
    assert "border-radius:0 !important" in text
    assert "mix-blend-mode:normal !important" in text
    assert "z-index:-1 !important" in text
