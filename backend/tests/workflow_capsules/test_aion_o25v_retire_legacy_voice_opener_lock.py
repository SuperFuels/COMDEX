from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"


def test_o25v_retires_o19_legacy_voice_opener_installers():
    text = APP.read_text(encoding="utf-8")
    assert "O19I legacy Tessaris Voice Opener retired by O25V" in text
    assert "O19M legacy voice onboarding UI retired by O25V" in text
    assert "O19N legacy opening speech retired by O25V" in text
    assert "O19O legacy opening trigger retired by O25V" in text
    assert "__aionO25VLegacyVoiceOpenerRetired" in text


def test_o25v_o20c_routes_to_o25u_not_o19():
    text = APP.read_text(encoding="utf-8")
    start = text.index("function openConversation(mode = \"start_with_aion\")")
    end = text.index("function closeConversation()", start)
    block = text[start:end]
    assert "O20C old conversation takeover is retired" in block
    assert "__aionO25UConversationOpen = true" in block
    assert "aion.o25u.current_terminal_open.v1" in block
    assert "startAionO19OOpeningFromBeginning" not in block
    assert "data-aion-o19i-play-stage" not in block


def test_o25v_o25u_selector_does_not_use_o20c_old_trigger():
    text = APP.read_text(encoding="utf-8")
    start = text.index("function renderBusinessEntryModeSelector()")
    end = text.index("window.renderBusinessEntryModeSelector = renderBusinessEntryModeSelector", start)
    block = text[start:end]
    assert "data-aion-o25u-startup-selector" in block
    assert "data-aion-o20c-open-conversation" not in block
    assert "data-aion-business-entry-mode=\"small_business_growth\"" in block


def test_o25v_js_syntax():
    subprocess.run(["node", "--check", str(APP)], cwd=ROOT, check=True)
