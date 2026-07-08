from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/aion_voice_bundle_python_framework_o24f.py"
MANIFEST = ROOT / ".runtime/voice_runtime_tests/o24f/bundle_python_framework_manifest.json"


def test_o24f_script_exists_and_documents_framework_relink_contract():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "O24F" in text
    assert "bundle_python_framework_and_relink_app_python" in text
    assert "install_name_tool" in text
    assert "codesign_runtime" in text
    assert "codesign" in text
    assert "@executable_path/../Frameworks/Python.framework/Versions/3.12/Python" in text
    assert ".o24e_symlink_backups" in text
    assert "aion_voice_relocation_hardening_o24b.py" in text
    assert "aion_voice_self_contained_runtime_audit_o24c.py" in text
    assert "aion_voice_native_dependency_audit_o24d.py" in text


def test_o24f_manifest_proves_framework_bundled_and_python_relinked():
    assert MANIFEST.exists(), "Run scripts/aion_voice_bundle_python_framework_o24f.py first."

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert data["phase"] == "O24F"
    assert data["ok"] is True
    assert data["business_context_hardcoded"] is False

    assert data["framework"]["bundled_framework_exists"] is True
    assert data["framework"]["bundled_framework_dylib_exists"] is True

    assert data["backup_cleanup"]["after"]["exists"] is False
    assert data["codesign"]["python"]["returncode"] == 0
    assert data["codesign"]["python"]["verify_returncode"] == 0
    assert data["codesign"]["Python"]["returncode"] == 0
    assert data["codesign"]["Python"]["verify_returncode"] == 0
    assert "framework_directory_codesign_note" in data

    assert data["app_python_otool_after"]["external_dependencies"] == []
    assert data["new_dylib"] in json.dumps(data["app_python_otool_after"])
    assert data["old_dylib"] not in json.dumps(data["app_python_otool_after"])

    assert data["packaged_readiness"]["ok"] is True
    assert data["python_probe"]["version_info"][0:2] == [3, 12]
    assert data["release_ready"] is True
    assert data["release_blockers"] == []


def test_o24f_manifest_proves_o24b_o24c_o24d_pass_after_relink():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    audits = data["post_relink_audits"]

    assert audits["o24b_ok"] is True
    assert audits["o24b_relocated_path_used"] is True

    assert audits["o24c_release_ready"] is True
    assert audits["o24c_release_blockers"] == []

    assert audits["o24d_release_ready"] is True
    assert audits["o24d_release_blockers"] == []
    assert audits["o24d_external_dependency_count"] == 0


def test_o24f_manifest_keeps_no_hidden_download_policy_locked():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    policy = data["download_policy"]

    assert policy["hidden_huggingface_downloads_allowed"] is False
    assert policy["hidden_transformers_downloads_allowed"] is False
    assert policy["hidden_spacy_downloads_allowed"] is False
    assert policy["hidden_elevenlabs_fallback_allowed"] is False
    assert policy["hidden_browser_speech_fallback_allowed"] is False


def test_o24f_is_business_agnostic():
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
