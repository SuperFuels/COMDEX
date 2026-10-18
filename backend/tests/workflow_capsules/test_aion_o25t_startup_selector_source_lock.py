from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"


def test_o25t_startup_selector_is_direct_route_source():
    text = APP.read_text(encoding="utf-8")
    start = text.index("function renderBusinessEntryModeSelector()")
    end = text.index("window.renderBusinessEntryModeSelector = renderBusinessEntryModeSelector", start)
    block = text[start:end]
    assert "AION O25U:" in block or "AION O25T: startup selector is the direct route source-of-truth" in block
    assert "data-aion-o25u-startup-selector" in block or "data-aion-o25t-startup-selector" in block
    assert "data-aion-o25u-current-terminal" in block
    assert "I have a business" in block
    assert "I have an idea" in block
    assert "Generate me an idea" in block
    assert "renderAionO25DBusinessFoundationConversationPanel" not in block
    assert "Business Twin Setup" not in block


def test_o25t_startup_selector_keeps_voice_click_only():
    text = APP.read_text(encoding="utf-8")
    assert 'startLocalOpeningVoice("foundation-active-tab")' not in text
    assert 'startOnce("page-mounted")' not in text
    assert "business-start-click" in text
    assert "click-only by O25S" in text


def test_o25t_disables_o25r_interval_rescue():
    text = APP.read_text(encoding="utf-8")
    assert 'setInterval(() => rescueIfBlank("interval"), 2500)' not in text
    assert "interval disabled by O25T" in text


def test_o25t_js_syntax():
    subprocess.run(["node", "--check", str(APP)], cwd=ROOT, check=True)
