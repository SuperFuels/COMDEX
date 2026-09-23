from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o18af_style_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18AF FORCE DEPARTMENT MARKETING STYLE LOCK" in text
    assert "aion-o18af-force-department-marketing-style" in text
    assert "__debugAionO18AFForceDepartmentMarketingStyle" in text

def test_o18af_targets_both_o18ac_and_o18ad():
    text = APP.read_text(encoding="utf-8")
    assert '[data-aion-o18ac-department]' in text
    assert '[data-aion-o18ad-department]' in text
    assert '[data-aion-o18ac-cockpit="true"]' in text
    assert '[data-aion-o18ad-cockpit="true"]' in text

def test_o18af_slimline_values():
    text = APP.read_text(encoding="utf-8")
    assert "font-size:13px !important" in text
    assert "padding:12px 14px !important" in text
    assert "height:22px !important" in text
    assert "max-width:178px !important" in text
