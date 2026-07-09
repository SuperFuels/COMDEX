from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
BRIDGE = ROOT / "backend/modules/aion_voice/voice_worker_bridge.py"
API = ROOT / "backend/modules/aion_voice/api.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_o25i_call_voice_worker_accepts_env_contract():
    text = read(BRIDGE)
    start = text.index("def call_voice_worker(")
    end = text.index("def synthesize_with_worker", start)
    block = text[start:end]

    assert "env: dict[str, str] | None = None" in block
    assert "merged_env = voice_worker_environment()" in block
    assert "merged_env.update" in block
    assert "env=merged_env" in block


def test_o25i_synthesize_worker_keeps_app_local_env_paths():
    text = read(BRIDGE)
    start = text.index("def synthesize_with_worker")
    end = text.index("def transcribe_with_worker", start)
    block = text[start:end]

    assert "env=voice_worker_environment()" in block
    assert "AION_VOICE_BUNDLE_ROOT" in text
    assert "AION_KOKORO_MODEL_PATH" in text
    assert "AION_KOKORO_CONFIG_PATH" in text
    assert "AION_KOKORO_VOICE_PATH" in text


def test_o25i_api_still_routes_tts_through_worker_first():
    text = read(API)
    assert "synthesize_with_worker" in text
    assert "AION_VOICE_WORKER_ENABLED" in text
    assert "worker_result = synthesize_with_worker" in text


def test_o25i_syntax_checks_clean():
    subprocess.run([sys.executable, "-m", "py_compile", str(BRIDGE)], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "py_compile", str(API)], cwd=ROOT, check=True)


def test_o25i_worker_request_writer_exists():
    text = read(BRIDGE)
    assert "def _write_worker_request" in text
    assert '"mode": str(mode)' in text
    assert '"operation": str(mode)' in text
    assert "request_path.write_text" in text
