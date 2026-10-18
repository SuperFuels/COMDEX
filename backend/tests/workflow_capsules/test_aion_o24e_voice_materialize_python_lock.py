from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/aion_voice_materialize_python_o24e.py"
MANIFEST = ROOT / ".runtime/voice_runtime_tests/o24e/materialize_python_manifest.json"


def test_o24e_script_exists_and_documents_python_materialization():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "O24E" in text
    assert "materialize_app_bundle_python_executables_from_symlinks" in text
    assert "python3.12" in text
    assert ".o24e_symlink_backups" in text
    assert "python_binary_has_external_native_dependencies" in text


def test_o24e_manifest_proves_python_is_no_longer_symlink():
    assert MANIFEST.exists(), "Run scripts/aion_voice_materialize_python_o24e.py first."

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert data["phase"] == "O24E"
    assert data["ok"] is True
    assert data["business_context_hardcoded"] is False

    assert data["app_python"] == "desktop/mac/Tessaris.app/Contents/Resources/voice/python/bin/python"
    assert data["app_python_after"]["exists"] is True
    assert data["app_python_after"]["is_symlink"] is False
    assert data["python_probe"]["version_info"][0:2] == [3, 12]
    assert data["packaged_readiness"]["ok"] is True

    before = data["materialized"]["before"]
    after = data["materialized"]["after"]

    assert before["python"]["is_symlink"] is True
    assert after["python"]["is_symlink"] is False
    assert after["python3"]["is_symlink"] is False
    assert after["python3.12"]["is_symlink"] is False


def test_o24e_manifest_records_remaining_native_dependency_state():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert "python_otool" in data
    assert "external_dependencies" in data["python_otool"]
    assert "release_blockers" in data
    assert "required_next_fix" in data
    assert data["required_next_fix"]["re_run_o24c_and_o24d_after_materialization"] is True
    assert data["required_next_fix"]["re_run_relocation_hardening_after_materialization"] is True


def test_o24e_manifest_keeps_no_hidden_download_policy_locked():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    policy = data["download_policy"]

    assert policy["hidden_huggingface_downloads_allowed"] is False
    assert policy["hidden_transformers_downloads_allowed"] is False
    assert policy["hidden_spacy_downloads_allowed"] is False
    assert policy["hidden_elevenlabs_fallback_allowed"] is False
    assert policy["hidden_browser_speech_fallback_allowed"] is False


def test_o24e_is_business_agnostic():
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
