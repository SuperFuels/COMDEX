from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[3]
BRIDGE = ROOT / "backend/modules/aion_voice/voice_worker_bridge.py"
WORKER = ROOT / "scripts/aion_voice_worker.py"
SMOKE = ROOT / "scripts/aion_voice_staged_worker_paths_smoke.py"
MANIFEST = ROOT / ".runtime/voice_runtime_tests/o23i/staged_worker_paths_manifest.json"


def test_o23i_bridge_exports_bundle_asset_paths_to_worker_env():
    text = BRIDGE.read_text(encoding="utf-8")

    assert "AION_VOICE_BUNDLE_ROOT" in text
    assert "AION_KOKORO_MODEL_PATH" in text
    assert "AION_KOKORO_CONFIG_PATH" in text
    assert "AION_KOKORO_VOICE_PATH" in text
    assert "AION_SPACY_MODEL_PATH" in text
    assert "AION_WHISPER_MODEL_PATH" in text
    assert "voice_worker_environment" in text


def test_o23i_worker_has_bundle_probe_mode():
    text = WORKER.read_text(encoding="utf-8")

    assert "aion_o23i_bundle_probe" in text
    assert "aion-o23i-bundle-probe" in text
    assert "prove_worker_runs_from_staged_bundle_paths" in text
    assert "HF_HUB_OFFLINE" in text
    assert "TRANSFORMERS_OFFLINE" in text


def test_o23i_smoke_manifest_proves_worker_from_staged_paths():
    assert MANIFEST.exists(), "Run scripts/aion_voice_staged_worker_paths_smoke.py first."

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert data["phase"] == "O23I"
    assert data["ok"] is True
    assert data["business_context_hardcoded"] is False

    assert data["staged_python"] == "desktop/mac/voice_bundle_staging/voice/python/bin/python"
    assert data["worker_returncode"] == 0

    payload = data["worker_payload"]
    assert payload["ok"] is True
    assert payload["version_info"][0:2] == [3, 12]

    for key in [
        "AION_VOICE_BUNDLE_ROOT",
        "AION_KOKORO_MODEL_PATH",
        "AION_KOKORO_CONFIG_PATH",
        "AION_KOKORO_VOICE_PATH",
        "AION_SPACY_MODEL_PATH",
        "AION_WHISPER_MODEL_PATH",
    ]:
        assert payload["paths"][key]["exists"] is True

    assert payload["offline_env"]["HF_HUB_OFFLINE"] == "1"
    assert payload["offline_env"]["TRANSFORMERS_OFFLINE"] == "1"
    assert payload["offline_env"]["HF_DATASETS_OFFLINE"] == "1"
    assert payload["offline_env"]["AION_VOICE_NO_HIDDEN_DOWNLOADS"] == "true"
    assert payload["offline_env"]["AION_ELEVENLABS_ENABLED"] == "false"
    assert payload["offline_env"]["AION_BROWSER_SPEECH_FALLBACK_ENABLED"] == "false"


def test_o23i_is_business_agnostic():
    text = BRIDGE.read_text(encoding="utf-8") + "\n" + WORKER.read_text(encoding="utf-8") + "\n" + SMOKE.read_text(encoding="utf-8")

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
