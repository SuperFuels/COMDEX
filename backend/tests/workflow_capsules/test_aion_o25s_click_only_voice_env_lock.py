from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"


def test_o25s_o25o_has_no_active_tab_auto_voice():
    text = APP.read_text(encoding="utf-8")
    assert 'startLocalOpeningVoice("foundation-active-tab")' not in text
    assert "click-only by O25S" in text


def test_o25s_o25o_still_starts_voice_from_business_click():
    text = APP.read_text(encoding="utf-8")
    assert "business-start-click" in text
    assert "i have a business" in text.lower()
    assert "http://127.0.0.1:8080/api/aion/voice/tts" in text
    assert 'provider: "local"' in text


def test_o25s_o25q_has_no_page_mounted_auto_voice():
    text = APP.read_text(encoding="utf-8")
    assert 'startOnce("page-mounted")' not in text
    assert "click-only by O25R" in text


def test_o25s_js_syntax():
    subprocess.run(["node", "--check", str(APP)], cwd=ROOT, check=True)
