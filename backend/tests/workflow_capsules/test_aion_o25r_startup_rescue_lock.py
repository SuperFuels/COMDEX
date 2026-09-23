from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"


def test_o25r_removes_o25q_page_mounted_auto_voice():
    text = APP.read_text(encoding="utf-8")
    assert 'startOnce("page-mounted")' not in text
    assert "click-only by O25R" in text


def test_o25r_startup_white_screen_rescue_installed():
    text = APP.read_text(encoding="utf-8")
    assert "AION O25R — Startup selector white-screen rescue" in text
    assert "aion.o25r.startup_white_screen_rescue.v1" in text
    assert "data-aion-o25r-startup-rescue" in text
    assert "I have a business" in text
    assert "Generate me an idea" in text
    assert "restored startup selector after blank render" in text


def test_o25r_does_not_start_voice_on_page_load():
    text = APP.read_text(encoding="utf-8")
    o25r = text[text.index("/* AION O25R"):]
    assert "/api/aion/voice/tts" not in o25r
    assert "new Audio" not in o25r
    assert "audio.play" not in o25r


def test_o25r_js_syntax():
    subprocess.run(["node", "--check", str(APP)], cwd=ROOT, check=True)
