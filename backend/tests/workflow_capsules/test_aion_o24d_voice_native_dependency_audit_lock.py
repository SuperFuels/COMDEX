from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/aion_voice_native_dependency_audit_o24d.py"
MANIFEST = ROOT / ".runtime/voice_runtime_tests/o24d/native_dependency_audit_manifest.json"


def test_o24d_script_exists_and_documents_native_dependency_audit():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "O24D" in text
    assert "audit_native_binary_dependencies_for_packaged_voice_runtime" in text
    assert "otool" in text
    assert "/opt/homebrew" in text
    assert "must_embed_real_python_runtime_not_homebrew_symlink" in text
    assert "must_rewrite_or_bundle_external_dylibs" in text


def test_o24d_manifest_records_external_dependency_release_blocker():
    assert MANIFEST.exists(), "Run scripts/aion_voice_native_dependency_audit_o24d.py first."

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert data["phase"] == "O24D"
    assert data["ok"] is True
    assert data["business_context_hardcoded"] is False

    assert data["app_python"] == "desktop/mac/Tessaris.app/Contents/Resources/voice/python/bin/python"
    assert data["native_file_count"] > 0
    assert data["audited_count"] > 0

    # Before O24F, O24D records external native dependency blockers.
    # After O24F, the Python framework is bundled/relinked and this audit may become release-ready.
    if data["external_dependency_count"] == 0:
        assert data["release_ready"] is True
        assert data["release_blockers"] == []
        assert data["external_dependency_records"] == []
    else:
        assert data["release_ready"] is False
        assert "external_native_dependencies_present" in data["release_blockers"]

        blocker_blob = json.dumps(data["release_blockers"])
        assert (
            "app_python_symlink_present" in blocker_blob
            or "external_native_dependencies_present" in blocker_blob
        )

        blob = json.dumps(data["external_dependency_records"])
        assert "/opt/homebrew" in blob

    assert data["required_fix"]["must_embed_real_python_runtime_not_homebrew_symlink"] is True
    assert data["required_fix"]["must_rewrite_or_bundle_external_dylibs"] is True


def test_o24d_manifest_keeps_no_hidden_download_policy_locked():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    policy = data["download_policy"]

    assert policy["hidden_huggingface_downloads_allowed"] is False
    assert policy["hidden_transformers_downloads_allowed"] is False
    assert policy["hidden_spacy_downloads_allowed"] is False
    assert policy["hidden_elevenlabs_fallback_allowed"] is False
    assert policy["hidden_browser_speech_fallback_allowed"] is False


def test_o24d_is_business_agnostic():
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
