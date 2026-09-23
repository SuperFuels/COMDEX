from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/aion_voice_bundle_staging.py"
MANIFEST = ROOT / "desktop/mac/voice_bundle_staging/voice/manifest.json"
VOICE_ROOT = ROOT / "desktop/mac/voice_bundle_staging/voice"


def test_o23b_o23d_staging_script_exists_and_targets_app_bundle_layout():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "O23B_O23C_O23D" in text
    assert "voice_bundle_staging" in text
    assert "kokoro-v1_0.pth" in text
    assert "af_heart.pt" in text
    assert "en_core_web_sm" in text
    assert "faster-whisper-base" in text
    assert "Tessaris.app/Contents/Resources/voice" in text


def test_o23b_o23d_staged_required_assets_exist():
    assert MANIFEST.exists(), "Run scripts/aion_voice_bundle_staging.py first."

    required = [
        VOICE_ROOT / "kokoro/kokoro-v1_0.pth",
        VOICE_ROOT / "kokoro/config.json",
        VOICE_ROOT / "kokoro/voices/af_heart.pt",
        VOICE_ROOT / "spacy/en_core_web_sm",
        VOICE_ROOT / "whisper/base",
        VOICE_ROOT / "manifest.json",
    ]

    for path in required:
        assert path.exists(), f"Missing staged voice asset: {path}"


def test_o23b_o23d_manifest_has_hashes_and_download_policy():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert data["ok"] is True
    assert data["phase"] == "O23B_O23C_O23D"
    assert data["python_runtime_bundled_in_this_step"] is False
    
    assert data["python_runtime_next_step"] in {"O23E", "O23F"}

    if data["python_runtime_next_step"] == "O23F":
        assert data["python_runtime_strategy"]["phase"] == "O23E"
        assert data["python_runtime_strategy"]["do_not_commit_dev_venv"] is True
    assert data["business_context_hardcoded"] is False

    copied = data["copied"]
    assert copied["kokoro_model"]["sha256"]
    assert copied["kokoro_voice_af_heart"]["sha256"]
    assert copied["kokoro_config"]["sha256"]
    assert copied["spacy_en_core_web_sm"]["tree_sha256"]
    assert copied["faster_whisper_base"]["tree_sha256"]

    policy = data["download_policy"]
    assert policy["packaged_mode_hidden_huggingface_downloads_allowed"] is False
    assert policy["packaged_mode_hidden_spacy_downloads_allowed"] is False
    assert policy["packaged_mode_hidden_elevenlabs_fallback_allowed"] is False


def test_o23b_o23d_manifest_is_business_agnostic():
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
