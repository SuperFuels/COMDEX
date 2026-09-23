from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[3]
CHECKER = ROOT / "backend/modules/aion_voice/voice_startup_readiness.py"
SMOKE = ROOT / "scripts/aion_voice_startup_readiness_smoke.py"
MANIFEST = ROOT / ".runtime/voice_runtime_tests/o23g/startup_readiness_manifest.json"


def test_o23g_checker_exists_and_tracks_required_assets():
    text = CHECKER.read_text(encoding="utf-8")

    assert "AION_O23G_VOICE_STARTUP_READINESS_VERSION" in text
    assert "kokoro/kokoro-v1_0.pth" in text
    assert "kokoro/config.json" in text
    assert "kokoro/voices/af_heart.pt" in text
    assert "spacy/en_core_web_sm" in text
    assert "whisper/base" in text
    assert "manifest.json" in text
    assert "python_is_3_12" in text


def test_o23g_checker_tracks_required_imports_and_fallback_bans():
    text = CHECKER.read_text(encoding="utf-8")

    for token in [
        "kokoro",
        "soundfile",
        "faster_whisper",
        "ctranslate2",
        "av",
        "torch",
        "spacy",
        "numpy",
    ]:
        assert token in text

    assert "no_elevenlabs_fallback" in text
    assert "no_browser_speech_fallback" in text
    assert "packaged_mode_does_not_fallback_to_dev_venv" in text


def test_o23g_smoke_manifest_proves_staging_ready_and_packaged_clear_missing_runtime():
    assert MANIFEST.exists(), "Run scripts/aion_voice_startup_readiness_smoke.py first."

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert data["phase"] == "O23G"
    assert data["ok"] is True
    assert data["business_context_hardcoded"] is False

    assert data["staging_readiness"]["ok"] is True
    assert data["packaged_missing_runtime_is_clear"] is True

    policy = data["download_policy"]
    assert policy["hidden_huggingface_downloads_allowed"] is False
    assert policy["hidden_spacy_downloads_allowed"] is False
    assert policy["hidden_elevenlabs_fallback_allowed"] is False
    assert policy["hidden_browser_speech_fallback_allowed"] is False


def test_o23g_is_business_agnostic():
    text = CHECKER.read_text(encoding="utf-8") + "\n" + SMOKE.read_text(encoding="utf-8")

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
