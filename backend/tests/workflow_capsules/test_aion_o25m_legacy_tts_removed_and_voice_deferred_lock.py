from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop" / "mac" / "src" / "app.js"
MAIN = ROOT / "backend" / "main.py"


def test_o25m_backend_main_no_legacy_direct_tts_decorator():
    text = MAIN.read_text(encoding="utf-8")
    assert '@app.post("/api/aion/voice/tts")' not in text
    assert "@app.post('/api/aion/voice/tts')" not in text
    assert '@router.post("/api/aion/voice/tts")' not in text
    assert "legacy-elevenlabs-disabled" in text


def test_o25m_frontend_final_authority_installed():
    text = APP.read_text(encoding="utf-8")
    assert "AION O25M — Backend-Ready Voice Start Final Authority" in text
    assert "waitForBackendReady" in text
    assert "http://127.0.0.1:8080/health" in text
    assert "aionO25MStartVoiceAfterBackendReady" in text
    assert "beginAionO25FBackendReadyProxy" in text
    assert "aion.o25m.backend_ready_voice_start_final_authority.v2" in text


def test_o25m_eager_o25f_calls_are_deferred_before_o25m():
    text = APP.read_text(encoding="utf-8")
    cut = text.find("AION O25M")
    assert cut != -1
    prefix = text[:cut]
    assert "window.__aionO25FDeferredAutomaticStartRequested = true" in prefix
    assert not re.search(r"setTimeout\(\s*\(\)\s*=>\s*beginAionO25FAutomaticConversation\(\)", prefix)
    assert not re.search(r"(?<!function\s)(?<!async\sfunction\s)\bbeginAionO25FAutomaticConversation\(\)\s*;", prefix)


def test_o25m_no_backend_refused_literal_left_in_o25k_or_o25m():
    text = APP.read_text(encoding="utf-8")
    idx = text.find("AION O25K")
    if idx != -1:
      block = text[idx:text.find("AION O25M", idx) if text.find("AION O25M", idx) != -1 else len(text)]
      assert "net::ERR_CONNECTION_REFUSED" not in block
    m = text.find("AION O25M")
    assert m != -1
    assert "net::ERR_CONNECTION_REFUSED" not in text[m:]
