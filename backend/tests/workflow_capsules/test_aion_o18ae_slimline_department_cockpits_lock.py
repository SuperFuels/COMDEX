from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o18ae_slimline_style_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18AE SLIMLINE DEPARTMENT CONVERSATION COCKPITS LOCK" in text
    assert "aion-o18ae-slimline-department-conversation-cockpits-style" in text
    assert "__debugAionO18AESlimlineDepartmentCockpits" in text
    assert "[data-aion-o18ad-cockpit=\"true\"]" in text

def test_o18ae_matches_marketing_slimline_proportions():
    text = APP.read_text(encoding="utf-8")
    assert "font-size:13px !important" in text
    assert "padding:12px 14px !important" in text
    assert "width:178px !important" in text
    assert "height:230px !important" in text
    assert "height:22px !important" in text
