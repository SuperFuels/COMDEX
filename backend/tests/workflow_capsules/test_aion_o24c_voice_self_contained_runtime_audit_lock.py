from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/aion_voice_self_contained_runtime_audit_o24c.py"
MANIFEST = ROOT / ".runtime/voice_runtime_tests/o24c/self_contained_runtime_audit_manifest.json"


def test_o24c_script_exists_and_documents_self_contained_runtime_audit():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "O24C" in text
    assert "audit_if_tessaris_app_voice_runtime_is_self_contained" in text
    assert "Tessaris.app/Contents/Resources/voice/python/bin/python" in text
    assert "/opt/homebrew" in text
    assert "must_replace_symlinked_python_with_relocatable_or_embedded_python" in text


def test_o24c_manifest_records_self_contained_runtime_release_state():
    assert MANIFEST.exists(), "Run scripts/aion_voice_self_contained_runtime_audit_o24c.py first."

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert data["phase"] == "O24C"
    assert data["ok"] is True
    assert data["business_context_hardcoded"] is False

    assert data["app_python"] == "desktop/mac/Tessaris.app/Contents/Resources/voice/python/bin/python"
    assert data["packaged_readiness"]["ok"] is True

    # O24C is an audit. Before O24F it records blockers; after O24F it should become release-ready.
    if data["release_ready"] is True:
        assert data["release_blockers"] == []
        assert data["python_state"]["is_symlink"] is False
        assert data["python_state"]["inside_voice_bundle"] is True
        assert data["external_symlinks"] == []
    else:
        assert data["release_blockers"], "O24C should record blockers until full runtime self-containment is complete."
        blocker_blob = json.dumps(data["release_blockers"])
        assert (
            "app_python_is_symlink" in blocker_blob
            or "app_python_resolves_to_external_runtime" in blocker_blob
            or "voice_bundle_contains_external_symlinks" in blocker_blob
            or "external_native_dependencies_present" in blocker_blob
            or "packaged_readiness_not_passing" in blocker_blob
        )

    assert data["required_fix"]["must_replace_symlinked_python_with_relocatable_or_embedded_python"] is True
    assert data["required_fix"]["must_not_resolve_to_homebrew_or_dev_machine_runtime"] is True

def test_o24c_manifest_keeps_no_hidden_download_policy_locked():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    policy = data["download_policy"]

    assert policy["hidden_huggingface_downloads_allowed"] is False
    assert policy["hidden_transformers_downloads_allowed"] is False
    assert policy["hidden_spacy_downloads_allowed"] is False
    assert policy["hidden_elevenlabs_fallback_allowed"] is False
    assert policy["hidden_browser_speech_fallback_allowed"] is False


def test_o24c_is_business_agnostic():
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
