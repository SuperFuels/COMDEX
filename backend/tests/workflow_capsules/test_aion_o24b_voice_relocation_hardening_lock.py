from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/aion_voice_relocation_hardening_o24b.py"
MANIFEST = ROOT / ".runtime/voice_runtime_tests/o24b/relocation_hardening_manifest.json"


def test_o24b_script_exists_and_documents_relocation_contract():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "O24B" in text
    assert "prove_tessaris_app_voice_runtime_survives_relocation" in text
    assert "desktop/mac/Tessaris.app" in text
    assert ".runtime/voice_runtime_tests/o24b/relocated_app" in text
    assert "relocated_path_used" in text
    assert "source_voice_root_leaked_into_runtime_probe" in text


def test_o24b_script_locks_required_assets_and_imports():
    text = SCRIPT.read_text(encoding="utf-8")

    for token in [
        "kokoro",
        "soundfile",
        "faster_whisper",
        "ctranslate2",
        "av",
        "torch",
        "spacy",
        "numpy",
        "kokoro/kokoro-v1_0.pth",
        "kokoro/config.json",
        "kokoro/voices/af_heart.pt",
        "spacy/en_core_web_sm",
        "whisper/base",
    ]:
        assert token in text


def test_o24b_manifest_proves_relocated_runtime_candidate():
    assert MANIFEST.exists(), "Run scripts/aion_voice_relocation_hardening_o24b.py first."

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert data["phase"] == "O24B"
    assert data["ok"] is True
    assert data["business_context_hardcoded"] is False

    assert data["relocated_python_state"]["exists"] is True
    assert data["python_probe"]["version_info"][0:2] == [3, 12]
    assert data["packaged_readiness"]["ok"] is True
    assert data["worker_bundle_probe"]["ok"] is True
    assert data["relocated_path_used"] is True
    assert data["source_voice_root_leaked_into_runtime_probe"] is False

    for item in data["assets"].values():
        assert item["exists"] is True


def test_o24b_no_hidden_download_policy_remains_locked():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    policy = data["download_policy"]

    assert policy["hidden_huggingface_downloads_allowed"] is False
    assert policy["hidden_transformers_downloads_allowed"] is False
    assert policy["hidden_spacy_downloads_allowed"] is False
    assert policy["hidden_elevenlabs_fallback_allowed"] is False
    assert policy["hidden_browser_speech_fallback_allowed"] is False


def test_o24b_is_business_agnostic():
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
