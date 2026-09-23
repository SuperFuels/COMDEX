from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"


def test_o25u_route_source_has_selector_and_current_terminal():
    text = APP.read_text(encoding="utf-8")
    start = text.index("function renderBusinessEntryModeSelector()")
    end = text.index("/* END AION O19F RESTORE REAL BUSINESS ENTRY SELECTOR LOCK */", start)
    block = text[start:end]
    assert "AION O25U" in block
    assert "data-aion-o25u-startup-selector" in block
    assert "data-aion-o25u-current-terminal" in block
    assert "Business Foundation Conversation" in block
    assert "Tessaris Voice Opener" not in block
    assert "Welcome to Tessaris." not in block


def test_o25u_decommissions_old_auto_mount_and_intervals():
    text = APP.read_text(encoding="utf-8")
    assert "O25E old terminal auto-mount is decommissioned" in text
    assert "O25M no longer auto-starts voice" in text
    assert "O25H interval disabled" in text
    assert 'startVoiceAfterBackendReady("deferred-start")' not in text
    assert "setInterval(() => {\n    syncBodyState();\n    forceCanonicalTerminal();" not in text


def test_o25u_business_click_routes_to_current_terminal_and_o25o_voice():
    text = APP.read_text(encoding="utf-8")
    assert "aion.o25u.current_terminal_open.v1" in text
    assert "__aionO25UConversationOpen" in text
    assert 'window.aionO25OStartLocalOpeningVoice("business-start-click")' in text


def test_o25u_keeps_voice_click_only_no_page_load_starters():
    text = APP.read_text(encoding="utf-8")
    assert 'startLocalOpeningVoice("foundation-active-tab")' not in text
    assert 'startOnce("page-mounted")' not in text
    assert 'startVoiceAfterBackendReady("deferred-start")' not in text


def test_o25u_js_syntax():
    subprocess.run(["node", "--check", str(APP)], cwd=ROOT, check=True)
