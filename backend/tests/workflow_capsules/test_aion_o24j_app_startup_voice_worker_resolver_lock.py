from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HELPER = ROOT / "desktop/mac/src/aion_voice_worker_runtime.js"
SCRIPT = ROOT / "scripts/aion_voice_app_startup_resolver_o24j.py"
MANIFEST = ROOT / ".runtime/voice_runtime_tests/o24j/app_startup_voice_worker_resolver_manifest.json"


def load_manifest() -> dict:
    assert MANIFEST.exists(), "Run scripts/aion_voice_app_startup_resolver_o24j.py first."
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_o24j_helper_exists_and_exports_startup_contract():
    text = HELPER.read_text(encoding="utf-8")

    assert "createVoiceWorkerLaunchSpec" in text
    assert "findVoiceBundleRoot" in text
    assert "buildVoiceWorkerEnv" in text
    assert "app_local_packaged_worker" in text
    assert "AION_VOICE_NO_HIDDEN_DOWNLOADS" in text
    assert "AION_BROWSER_SPEECH_FALLBACK_ENABLED" in text
    assert "AION_ELEVENLABS_ENABLED" in text


def test_o24j_manifest_proves_startup_resolver_points_at_app_local_worker():
    data = load_manifest()

    assert data["ok"] is True
    assert data["phase"] == "O24J"
    assert data["release_ready"] is True
    assert data["release_blockers"] == []

    probe = data["probe"]
    assert probe["ok"] is True
    assert probe["launchMode"] == "app_local_packaged_worker"
    assert probe["pythonExists"] is True
    assert probe["workerExists"] is True
    assert probe["python"].endswith("desktop/mac/Tessaris.app/Contents/Resources/voice/python/bin/python")
    assert probe["worker"].endswith("desktop/mac/Tessaris.app/Contents/Resources/voice/runtime/scripts/aion_voice_worker.py")
    assert probe["cwd"].endswith("desktop/mac/Tessaris.app/Contents/Resources/voice/runtime")


def test_o24j_startup_resolver_locks_no_hidden_download_policy():
    data = load_manifest()
    env = data["probe"]["env"]

    assert env["AION_VOICE_RUNTIME_MODE"] == "packaged"
    assert env["AION_VOICE_NO_HIDDEN_DOWNLOADS"] == "true"
    assert env["HF_HUB_OFFLINE"] == "1"
    assert env["TRANSFORMERS_OFFLINE"] == "1"
    assert env["HF_DATASETS_OFFLINE"] == "1"
    assert env["AION_ELEVENLABS_ENABLED"] == "false"
    assert env["AION_BROWSER_SPEECH_FALLBACK_ENABLED"] == "false"

    assert data["download_policy"]["hidden_huggingface_downloads_allowed"] is False
    assert data["download_policy"]["hidden_browser_speech_fallback_allowed"] is False
    assert data["download_policy"]["hidden_elevenlabs_fallback_allowed"] is False


def test_o24j_is_business_agnostic():
    data = load_manifest()
    assert data["business_context_hardcoded"] is False

    text = HELPER.read_text(encoding="utf-8") + "\n" + SCRIPT.read_text(encoding="utf-8")
    forbidden = [
        "Home" + " Fixed",
        "Al" + "mería",
        "Mur" + "cia",
        "Mo" + "jácar",
        "per" + "gola",
        "car" + "port",
        "vil" + "la",
        "trades" + "men",
    ]
    for token in forbidden:
        assert token not in text
