from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/aion_voice_runtime_bundle_strategy.py"
STRATEGY_MANIFEST = ROOT / "desktop/mac/voice_bundle_staging/voice/python_runtime_manifest.o23e.json"
VOICE_MANIFEST = ROOT / "desktop/mac/voice_bundle_staging/voice/manifest.json"
STAGING_PYTHON = ROOT / "desktop/mac/voice_bundle_staging/voice/python/bin/python"


def test_o23e_runtime_strategy_script_exists_and_is_packaging_oriented():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "O23E" in text
    assert ".venv_voice" in text
    assert "Tessaris.app/Contents/Resources/voice/python/bin/python" in text
    assert "kokoro" in text
    assert "faster_whisper" in text
    assert "ctranslate2" in text
    assert "torch" in text
    assert "spacy" in text


def test_o23e_strategy_manifest_exists_and_blocks_bad_packaging_methods():
    assert STRATEGY_MANIFEST.exists(), "Run scripts/aion_voice_runtime_bundle_strategy.py first."
    data = json.loads(STRATEGY_MANIFEST.read_text(encoding="utf-8"))
    assert data["phase"] == "O23E"
    assert data["ok"] is True
    assert data["business_context_hardcoded"] is False
    forbidden = data["forbidden_runtime_build_methods"]
    assert "commit .venv_voice directly to normal git" in forbidden
    assert "silently pip install dependencies on customer machine" in forbidden
    assert "silently download model assets at first voice use" in forbidden
    assert "silently fall back to ElevenLabs" in forbidden
    assert "silently fall back to browser SpeechRecognition" in forbidden


def test_o23e_staging_python_launcher_exists_and_points_to_runtime_contract():
    assert STAGING_PYTHON.exists()
    text = STAGING_PYTHON.read_text(encoding="utf-8")
    assert ".venv_voice/bin/python" in text
    assert "Development/staging only" in text
    assert "Release packaging must replace this" in text


def test_o23e_voice_manifest_references_python_runtime_strategy():
    assert VOICE_MANIFEST.exists()
    data = json.loads(VOICE_MANIFEST.read_text(encoding="utf-8"))
    strategy = data["python_runtime_strategy"]
    assert strategy["phase"] == "O23E"
    assert strategy["do_not_commit_dev_venv"] is True
    assert strategy["release_requirement"] == "replace staging launcher with embedded or relocatable Python 3.12 runtime"
    assert data["python_runtime_next_step"] == "O23F"


def test_o23e_manifest_is_business_agnostic():
    text = SCRIPT.read_text(encoding="utf-8") + "\n" + STRATEGY_MANIFEST.read_text(encoding="utf-8")
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
