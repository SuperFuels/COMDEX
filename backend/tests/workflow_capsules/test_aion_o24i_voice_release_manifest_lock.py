from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/aion_voice_release_manifest_o24i.py"
MANIFEST = ROOT / ".runtime/voice_runtime_tests/o24i/voice_release_manifest.json"


def load_manifest() -> dict:
    assert MANIFEST.exists(), "Run scripts/aion_voice_release_manifest_o24i.py first."
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_o24i_script_exists_and_names_release_digest_contract():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "O24I" in text
    assert "create_release_manifest_and_packaging_digest_for_app_local_voice_runtime" in text
    assert "tree_sha256" in text
    assert "generated_runtime_staged" in text
    assert "business_context_hardcoded" in text


def test_o24i_manifest_proves_release_ready_voice_bundle_digest():
    data = load_manifest()

    assert data["ok"] is True
    assert data["phase"] == "O24I"
    assert data["release_ready"] is True
    assert data["release_blockers"] == []

    digest = data["packaging_digest"]
    assert digest["exists"] is True
    assert digest["file_count"] > 100
    assert digest["total_bytes"] > 100_000_000
    assert len(digest["tree_sha256"]) == 64


def test_o24i_manifest_links_o24f_o24g_o24h_release_ready_sources():
    data = load_manifest()

    sources = data["source_manifests"]
    assert sources["o24f"]["release_ready"] is True
    assert sources["o24g"]["release_ready"] is True
    assert sources["o24h"]["release_ready"] is True

    ready = data["prerequisite_ready"]
    assert ready["o24f_release_ready"] is True
    assert ready["o24g_release_ready"] is True
    assert ready["o24h_release_ready"] is True
    assert ready["o24h_tts_ok"] is True
    assert ready["o24h_stt_ok"] is True


def test_o24i_manifest_records_required_bundle_files_and_hashes():
    data = load_manifest()
    inventory = data["file_inventory"]

    for key in [
        "app_python",
        "app_python3",
        "app_python312",
        "python_framework_dylib",
        "app_worker",
        "kokoro_model",
        "kokoro_config",
        "kokoro_voice",
        "bundle_manifest",
    ]:
        state = inventory[key]
        assert state["exists"] is True
        assert state["is_symlink"] is False
        assert state["external_prefix_match"] is None
        assert len(state["sha256"]) == 64

    assert inventory["spacy_model"]["exists"] is True
    assert inventory["whisper_model"]["exists"] is True


def test_o24i_manifest_proves_no_external_python_native_dependencies():
    data = load_manifest()
    checks = data["native_dependency_checks"]

    for key in ["app_python", "app_python3", "app_python312", "python_framework_dylib"]:
        assert checks[key]["returncode"] == 0
        assert checks[key]["external_dependencies"] == []

    assert data["git_generated_staging_guard"]["generated_runtime_staged"] is False
    assert data["framework_id_hardening"]["after"]["external_dependencies"] == []


def test_o24i_download_policy_and_business_agnostic_lock():
    data = load_manifest()

    assert data["download_policy"]["hidden_huggingface_downloads_allowed"] is False
    assert data["download_policy"]["hidden_transformers_downloads_allowed"] is False
    assert data["download_policy"]["hidden_spacy_downloads_allowed"] is False
    assert data["download_policy"]["hidden_elevenlabs_fallback_allowed"] is False
    assert data["download_policy"]["hidden_browser_speech_fallback_allowed"] is False
    assert data["business_context_hardcoded"] is False

    text = SCRIPT.read_text(encoding="utf-8")
    forbidden = [
        "Home" + " Fixed",
        "Costa" + "Connect",
        "Costa" + "Conexion",
        "Al" + "mería",
        "Mur" + "cia",
        "Mo" + "jácar",
        "Al" + "box",
    ]
    for token in forbidden:
        assert token not in text
