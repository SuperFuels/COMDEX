from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def test_o25k_backend_ready_voice_authority_installed():
    text = read_app()
    assert "AION O25K — Backend-ready voice onboarding authority" in text
    assert "aion.o25k.backend_ready_voice_onboarding_authority.v1" in text
    assert "aionO25KWaitForBackendReady" in text
    assert "aionO25KStartBackendReadyFoundationVoice" in text


def test_o25k_waits_for_health_before_voice_tts():
    text = read_app()
    block = text[text.index("AION O25K — Backend-ready voice onboarding authority") :]
    assert "http://127.0.0.1:8080/health" in block
    assert "http://127.0.0.1:8080/api/aion/voice/tts" in block
    assert "await waitForAionLocalBackendReady" in block
    assert "backend ready; starting opening local voice" in block
    assert "net::ERR_CONNECTION_REFUSED" not in block


def test_o25k_wraps_legacy_o25f_starter():
    text = read_app()
    block = text[text.index("AION O25K — Backend-ready voice onboarding authority") :]
    assert "beginAionO25FAutomaticConversation" in block
    assert "__aionO25KWrapped" in block
    assert "wrapped O25F starter behind backend health" in block


def test_o25k_binds_business_start_buttons():
    text = read_app()
    block = text[text.index("AION O25K — Backend-ready voice onboarding authority") :]
    assert "i have a business" in block
    assert "startBackendReadyFoundationVoice" in block
    assert "addEventListener" in block


def test_o25k_syntax_clean():
    subprocess.run(["node", "--check", str(APP)], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "py_compile", "backend/main.py"], cwd=ROOT, check=True)
