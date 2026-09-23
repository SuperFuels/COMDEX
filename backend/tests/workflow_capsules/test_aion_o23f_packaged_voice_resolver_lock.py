from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[3]
BRIDGE = ROOT / "backend/modules/aion_voice/voice_worker_bridge.py"
SMOKE = ROOT / "scripts/aion_voice_packaged_resolver_smoke.py"
MANIFEST = ROOT / ".runtime/voice_runtime_tests/o23f/packaged_resolver_manifest.json"


def test_o23f_bridge_has_packaged_resolver_contract():
    text = BRIDGE.read_text(encoding="utf-8")

    assert "AION_O23F_PACKAGED_VOICE_RESOLVER_VERSION" in text
    assert "def voice_bundle_staging_root" in text
    assert "def voice_bundle_packaged_root" in text
    assert "def voice_bundle_root_from_env" in text
    assert "def resolve_voice_bundle_root" in text
    assert "def resolve_voice_python" in text
    assert "AION_VOICE_BUNDLE_ROOT" in text
    assert "AION_VOICE_RUNTIME_MODE" in text
    assert "AION_VOICE_PYTHON" in text
    assert "Tessaris.app" in text
    assert "Contents" in text
    assert "Resources" in text
    assert "voice_bundle_staging" in text


def test_o23f_default_voice_python_uses_resolver():
    text = BRIDGE.read_text(encoding="utf-8")

    assert "def default_voice_python() -> Path:" in text
    assert "return resolve_voice_python()" in text


def test_o23f_smoke_manifest_exists_and_proves_staging_resolution():
    assert MANIFEST.exists(), "Run scripts/aion_voice_packaged_resolver_smoke.py first."

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert data["phase"] == "O23F"
    assert data["ok"] is True
    assert data["business_context_hardcoded"] is False

    assert data["staging"]["python_exists"] is True
    assert data["resolution_cases"]["staging_mode"]["python"] == data["staging"]["python"]
    assert data["resolution_cases"]["bundle_root_override"]["python"] == data["staging"]["python"]
    assert data["resolution_cases"]["explicit_python_override"]["python"] == data["staging"]["python"]

    assert data["download_policy"]["packaged_mode_hidden_huggingface_downloads_allowed"] is False
    assert data["download_policy"]["packaged_mode_hidden_spacy_downloads_allowed"] is False
    assert data["download_policy"]["packaged_mode_hidden_elevenlabs_fallback_allowed"] is False


def test_o23f_resolver_is_business_agnostic():
    text = BRIDGE.read_text(encoding="utf-8") + "\n" + SMOKE.read_text(encoding="utf-8")

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
