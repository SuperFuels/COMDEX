# AION O24A LOCK: verifies embedded app runtime candidate builder.
from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/aion_voice_build_embedded_runtime_o24a.py"
MANIFEST = ROOT / ".runtime/voice_runtime_tests/o24a/embedded_runtime_build_manifest.json"


def test_o24a_builder_exists_and_targets_tessaris_app_voice_runtime():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "O24A" in text
    assert "build_actual_tessaris_app_embedded_voice_runtime_candidate" in text
    assert "desktop/mac/Tessaris.app/Contents/Resources/voice" in text
    assert "python/bin/python" in text
    assert ".venv_voice" in text
    assert "heavy_app_runtime_assets_should_not_be_committed_directly" in text


def test_o24a_builder_copies_required_voice_assets():
    text = SCRIPT.read_text(encoding="utf-8")

    for token in [
        "kokoro/kokoro-v1_0.pth",
        "kokoro/config.json",
        "kokoro/voices/af_heart.pt",
        "spacy/en_core_web_sm",
        "whisper/base",
        "manifest.json",
    ]:
        assert token in text


def test_o24a_manifest_proves_embedded_runtime_candidate_built():
    assert MANIFEST.exists(), "Run scripts/aion_voice_build_embedded_runtime_o24a.py first."

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert data["phase"] == "O24A"
    assert data["ok"] is True
    assert data["business_context_hardcoded"] is False

    assert data["app_voice_root"] == "desktop/mac/Tessaris.app/Contents/Resources/voice"
    assert data["app_python"] == "desktop/mac/Tessaris.app/Contents/Resources/voice/python/bin/python"

    assert data["runtime"]["python_exists"] is True
    assert data["python_probe"]["version_info"][0:2] == [3, 12]
    assert data["packaged_readiness"]["ok"] is True
    assert data["worker_bundle_probe"]["ok"] is True

    for item in data["assets"].values():
        assert item["target_exists"] is True


def test_o24a_no_hidden_download_policy_remains_locked():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    policy = data["download_policy"]

    assert policy["hidden_huggingface_downloads_allowed"] is False
    assert policy["hidden_transformers_downloads_allowed"] is False
    assert policy["hidden_spacy_downloads_allowed"] is False
    assert policy["hidden_elevenlabs_fallback_allowed"] is False
    assert policy["hidden_browser_speech_fallback_allowed"] is False


def test_o24a_is_business_agnostic():
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
