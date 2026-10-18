from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o18e_facetime_crop_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18E REAL AGENT FACETIME CROP LOCK" in text
    assert "aion-o18e-real-agent-facetime-crop-style" in text
    assert "__debugAionO18ERealAgentFaceTimeCrop" in text
    assert "MARKETING AGENT · LIVE" in text

def test_o18e_keeps_real_canvas_and_hides_fake_hud():
    text = APP.read_text(encoding="utf-8")
    assert '[data-aion-o18b-agent-figure="true"]' in text
    assert "display:none !important" in text
    assert "real_canvas_exists" in text
    assert "transform:scale(3.65) translateY(18px)" in text
    assert "border-radius:16px" in text
