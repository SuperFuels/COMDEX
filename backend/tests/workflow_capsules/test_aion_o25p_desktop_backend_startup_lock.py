from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
MAIN = ROOT / "desktop/mac/electron/main.js"
INDEX = ROOT / "desktop/mac/src/index.html"
APP = ROOT / "desktop/mac/src/app.js"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_o25p_spawn_uses_single_local_voice_env_object():
    text = read(MAIN)
    spawn_start = text.index("const proc = spawn(pythonBin")
    block = text[spawn_start: text.index("backendProc = proc", spawn_start)]
    assert block.count("env:") == 1
    assert "aionO25NLocalVoiceBackendEnv({" in block
    assert 'AION_VOICE_WORKER_ENABLED: "true"' in text
    assert 'AION_TTS_PROVIDER: "kokoro"' in text
    assert 'PYTHONPATH: projectRoot' in block
    assert 'TESSARIS_PROJECT_ROOT: projectRoot' in block


def test_o25p_renderer_loads_after_backend_start_attempt():
    text = read(MAIN)
    ready_start = text.index("app.whenReady().then(async () =>")
    block = text[ready_start:]
    assert "await ensureBackendRunning()" in block
    assert block.index("await ensureBackendRunning()") < block.index("createWindow()")
    assert "start backend before loading renderer" in block


def test_o25p_backend_health_route_matches_known_good_health():
    text = read(MAIN)
    assert 'const BACKEND_HEALTH_PATH = "/health";' in text


def test_o25p_csp_is_single_valid_connect_src_and_no_bad_self_directive():
    text = read(INDEX)
    assert "''self''" not in text
    assert "default-src;" not in text
    assert text.count("connect-src") == 1
    assert "media-src 'self' data: blob: file:" in text
    assert "http://127.0.0.1:8080" in text


def test_o25p_blocks_stale_business_placeholder_before_network():
    text = read(APP)
    assert "AION O25P — Final stale business placeholder fetch blocker" in text
    assert "stale_placeholder_business_id_blocked_before_network" in text
    assert "/api/aion/business/" in text
    assert "business_not_registered" in text
    assert "costa-conexion" in text


def test_o25p_js_syntax():
    subprocess.run(["node", "--check", str(MAIN)], cwd=ROOT, check=True)
    subprocess.run(["node", "--check", str(APP)], cwd=ROOT, check=True)
