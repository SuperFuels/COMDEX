from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/aion_voice_app_local_worker_o24g.py"
MANIFEST = ROOT / ".runtime/voice_runtime_tests/o24g/app_local_worker_manifest.json"


def test_o24g_script_exists_and_documents_app_local_worker_contract():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "O24G" in text
    assert "bundle_app_local_voice_worker_entrypoint" in text
    assert "APP_RUNTIME_ROOT" in text
    assert "APP_WORKER" in text
    assert "aion_voice_worker.py" in text
    assert "backend.modules.aion_voice.voice_download_policy" in text
    assert "aion-o23i-bundle-probe" in text
    assert "repo_worker_script_still_used" in text


def test_o24g_manifest_proves_app_local_worker_entrypoint():
    assert MANIFEST.exists(), "Run scripts/aion_voice_app_local_worker_o24g.py first."

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert data["phase"] == "O24G"
    assert data["ok"] is True
    assert data["release_ready"] is True
    assert data["release_blockers"] == []

    assert data["app_worker"] == "desktop/mac/Tessaris.app/Contents/Resources/voice/runtime/scripts/aion_voice_worker.py"
    assert data["copied"]["worker"]["exists"] is True
    assert data["copied"]["aion_voice_package"]["exists"] is True

    assert data["app_worker_imports_ok"] is True
    assert data["voice_imports_ok"] is True
    assert data["worker_probe_ok"] is True
    assert data["worker_python_is_app_python"] is True
    assert data["worker_uses_app_bundle_root"] is True
    assert data["repo_worker_used"] is False
    assert data["packaged_readiness"]["ok"] is True


def test_o24g_import_probe_uses_app_runtime_backend_not_repo_backend():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    imports = data["import_probe"]["imports"]

    for name in [
        "backend.modules.aion_voice.voice_download_policy",
        "backend.modules.aion_voice.voice_worker_bridge",
        "backend.modules.aion_voice.voice_startup_readiness",
    ]:
        assert imports[name]["found"] is True
        assert imports[name]["inside_app_runtime"] is True
        assert imports[name]["inside_repo"] is False


def test_o24g_keeps_no_hidden_download_policy_locked():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    policy = data["download_policy"]
    offline_env = data["worker_probe"]["offline_env"]

    assert policy["hidden_huggingface_downloads_allowed"] is False
    assert policy["hidden_transformers_downloads_allowed"] is False
    assert policy["hidden_spacy_downloads_allowed"] is False
    assert policy["hidden_elevenlabs_fallback_allowed"] is False
    assert policy["hidden_browser_speech_fallback_allowed"] is False

    assert offline_env["HF_HUB_OFFLINE"] == "1"
    assert offline_env["TRANSFORMERS_OFFLINE"] == "1"
    assert offline_env["HF_DATASETS_OFFLINE"] == "1"
    assert offline_env["AION_VOICE_NO_HIDDEN_DOWNLOADS"] == "true"
    assert offline_env["AION_ELEVENLABS_ENABLED"] == "false"
    assert offline_env["AION_BROWSER_SPEECH_FALLBACK_ENABLED"] == "false"


def test_o24g_is_business_agnostic():
    text = SCRIPT.read_text(encoding="utf-8")

    forbidden = [
        "Home" + " Fixed",
        "Al" + "meria",
        "Al" + "mería",
        "Mur" + "cia",
        "Mo" + "jacar",
        "per" + "gola",
        "paint" + "ing",
        "construct" + "ion",
        "roof" + " repair",
    ]

    for token in forbidden:
        assert token not in text
