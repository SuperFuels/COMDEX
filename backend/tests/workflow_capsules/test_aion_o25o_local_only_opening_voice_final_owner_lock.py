from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop/mac/src/app.js"


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def o25o_block() -> str:
    text = read_app()
    start = text.index("AION O25O — Local-Only Opening Voice Final Owner")
    return text[start:]


def test_o25o_local_only_opening_voice_final_owner_installed():
    block = o25o_block()
    assert "aion.o25o.local_only_opening_voice_final_owner.v1" in block
    assert "aionO25OStartLocalOpeningVoice" in block
    assert "O25O local-only opening voice final owner installed" in block


def test_o25o_uses_direct_local_backend_request_not_old_speakaion_path():
    block = o25o_block()
    assert "XMLHttpRequest" in block
    assert "http://127.0.0.1:8080/api/aion/voice/tts" in block
    assert 'provider: "local"' in block
    assert 'voice: "af_heart"' in block
    assert "speakAion(" not in block
    assert "duplicate_voice_request_blocked" not in block


def test_o25o_suppresses_o25k_and_delegates_o25m():
    block = o25o_block()
    assert "aionO25KStartBackendReadyFoundationVoice" in block
    assert "aionO25MStartVoiceAfterBackendReady" in block
    assert "O25K voice starter suppressed" in block
    assert "O25M delegated to O25O" in block


def test_o25o_js_syntax():
    subprocess.run(["node", "--check", str(APP)], cwd=ROOT, check=True)
