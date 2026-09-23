from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/aion_voice_asset_discovery.py"
MANIFEST = ROOT / "desktop/mac/voice/manifest.o23a.json"


def test_o23a_asset_discovery_script_exists_and_is_packaging_oriented():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "O23A" in text
    assert ".venv_voice/bin/python" in text
    assert "kokoro-v1_0.pth" in text
    assert "af_heart.pt" in text
    assert "en_core_web_sm" in text
    assert "faster_whisper" in text
    assert "Tessaris.app/Contents/Resources/voice" in text


def test_o23a_manifest_written_with_no_hidden_download_policy():
    assert MANIFEST.exists(), "Run scripts/aion_voice_asset_discovery.py first."

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    policy = data["download_policy"]

    assert data["phase"] == "O23A"
    assert policy["packaged_mode_hidden_huggingface_downloads_allowed"] is False
    assert policy["packaged_mode_hidden_spacy_downloads_allowed"] is False
    assert policy["packaged_mode_hidden_elevenlabs_fallback_allowed"] is False
    assert data["business_context_hardcoded"] is False


def test_o23a_manifest_tracks_required_voice_assets():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    summary = data["required_summary"]

    for key in [
        "python_3_12_runtime",
        "kokoro_package",
        "soundfile_package",
        "faster_whisper_package",
        "torch_package",
        "spacy_package",
        "kokoro_model_found",
        "kokoro_voice_af_heart_found",
        "kokoro_config_found",
        "spacy_en_core_web_sm_found",
        "whisper_base_or_small_found",
    ]:
        assert key in summary

    targets = data["packaging_targets"]
    assert targets["bundle_root"] == "Tessaris.app/Contents/Resources/voice"
    assert targets["python_runtime"].endswith("/voice/python/bin/python")
    assert targets["manifest"].endswith("/voice/manifest.json")


def test_o23a_manifest_is_business_agnostic():
    text = SCRIPT.read_text(encoding="utf-8") + "\n" + MANIFEST.read_text(encoding="utf-8")

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
