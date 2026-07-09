from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"


def test_o25w_startup_uses_big_central_graphic():
    text = APP.read_text(encoding="utf-8")
    start = text.index("function renderBusinessEntryModeSelector()")
    end = text.index("window.renderBusinessEntryModeSelector = renderBusinessEntryModeSelector", start)
    block = text[start:end]
    assert "data-aion-o25w-big-graphic-startup" in block
    assert "data-aion-o25w-central-graphic" in block
    assert "<svg viewBox=\"0 0 520 520\"" in block
    assert "BOARDROOM" in block
    assert "AGENTS" in block
    assert "WORKFLOWS" in block
    assert "TWIN" in block
    assert "∞" in block


def test_o25w_keeps_working_business_click_marker():
    text = APP.read_text(encoding="utf-8")
    start = text.index("function renderBusinessEntryModeSelector()")
    end = text.index("window.renderBusinessEntryModeSelector = renderBusinessEntryModeSelector", start)
    block = text[start:end]
    assert 'data-aion-business-entry-mode="small_business_growth"' in block
    assert 'data-aion-o25u-start-business="true"' in block
    assert "data-aion-o25u-current-terminal" in block


def test_o25w_does_not_restore_legacy_opener_trigger():
    text = APP.read_text(encoding="utf-8")
    start = text.index("function renderBusinessEntryModeSelector()")
    end = text.index("window.renderBusinessEntryModeSelector = renderBusinessEntryModeSelector", start)
    block = text[start:end]
    assert "data-aion-o20c-open-conversation" not in block
    assert "Tessaris Voice Opener" not in block
    assert "Welcome to Tessaris." not in block


def test_o25w_js_syntax():
    subprocess.run(["node", "--check", str(APP)], cwd=ROOT, check=True)
