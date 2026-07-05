from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o18w_marketing_chrome_removed_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18W REMOVE MARKETING COCKPIT CHROME LOCK" in text
    assert "aion-o18w-remove-marketing-cockpit-chrome-style" in text
    assert "__debugAionO18WMarketingChromeRemoved" in text
    assert "Spatial Marketing Boardroom label" in text
    assert "Terminal context-packet label" in text

def test_o18w_hides_header_and_badges_not_package():
    text = APP.read_text(encoding="utf-8")
    assert '[data-aion-o17e-marketing-pilot-cockpit="true"] > div:first-of-type' in text
    assert '[data-aion-o17e-marketing-pilot-terminal="true"] [data-aion-council-terminal-header="true"] > div:first-child' in text
    assert "package_exists" in text
    assert "agent_inside_terminal" in text
