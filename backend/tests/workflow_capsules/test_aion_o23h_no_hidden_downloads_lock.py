from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / "backend/modules/aion_voice/voice_download_policy.py"
BRIDGE = ROOT / "backend/modules/aion_voice/voice_worker_bridge.py"
WORKER = ROOT / "scripts/aion_voice_worker.py"
SMOKE = ROOT / "scripts/aion_voice_no_hidden_downloads_smoke.py"
MANIFEST = ROOT / ".runtime/voice_runtime_tests/o23h/no_hidden_downloads_manifest.json"


def test_o23h_policy_module_exists_and_sets_offline_env():
    text = POLICY.read_text(encoding="utf-8")

    assert "AION_O23H_NO_HIDDEN_DOWNLOADS_VERSION" in text
    assert "HF_HUB_OFFLINE" in text
    assert "TRANSFORMERS_OFFLINE" in text
    assert "HF_DATASETS_OFFLINE" in text
    assert "HF_HUB_DISABLE_TELEMETRY" in text
    assert "AION_VOICE_NO_HIDDEN_DOWNLOADS" in text
    assert "AION_ELEVENLABS_ENABLED" in text
    assert "AION_BROWSER_SPEECH_FALLBACK_ENABLED" in text


def test_o23h_bridge_and_worker_apply_policy():
    bridge = BRIDGE.read_text(encoding="utf-8")
    worker = WORKER.read_text(encoding="utf-8")

    assert "build_voice_download_policy_env" in bridge
    assert "def voice_worker_environment" in bridge
    assert "env=voice_worker_environment()" in bridge

    assert "apply_voice_download_policy" in worker
    assert "AION O23H" in worker


def test_o23h_smoke_manifest_locks_download_policy():
    assert MANIFEST.exists(), "Run scripts/aion_voice_no_hidden_downloads_smoke.py first."

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert data["phase"] == "O23H"
    assert data["ok"] is True
    assert data["business_context_hardcoded"] is False

    env = data["worker_environment"]
    assert env["HF_HUB_OFFLINE"] == "1"
    assert env["TRANSFORMERS_OFFLINE"] == "1"
    assert env["HF_DATASETS_OFFLINE"] == "1"
    assert env["AION_VOICE_NO_HIDDEN_DOWNLOADS"] == "true"
    assert env["AION_ELEVENLABS_ENABLED"] == "false"
    assert env["AION_BROWSER_SPEECH_FALLBACK_ENABLED"] == "false"

    policy = data["download_policy"]
    assert policy["hidden_huggingface_downloads_allowed"] is False
    assert policy["hidden_transformers_downloads_allowed"] is False
    assert policy["hidden_spacy_downloads_allowed"] is False
    assert policy["hidden_elevenlabs_fallback_allowed"] is False
    assert policy["hidden_browser_speech_fallback_allowed"] is False


def test_o23h_is_business_agnostic():
    text = POLICY.read_text(encoding="utf-8") + "\n" + SMOKE.read_text(encoding="utf-8")

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
