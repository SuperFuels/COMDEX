from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACKAGING = ROOT / "packaging" / "aion_sovereign_brain_bootstrap"
BUILDER = ROOT / "scripts" / "build_aion_sovereign_brain_offline_macos_arm64.py"


def test_release_declares_real_offline_reference_bundle() -> None:
    release = json.loads((PACKAGING / "release_manifest.json").read_text(encoding="utf-8"))
    assert release["version"] == "0.15.0"
    assert "CPython 3.13" in release["offline_reference_bundle"]
    assert "Gemma 3 1B" in release["offline_reference_bundle"]


def test_offline_dependencies_are_exactly_locked() -> None:
    lines = [
        line.strip()
        for line in (PACKAGING / "requirements-offline-macos-arm64-py313.txt").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert lines
    assert all("==" in line and "://" not in line for line in lines)


def test_builder_pins_runtime_digest_and_forbids_cloud_fallback() -> None:
    source = BUILDER.read_text(encoding="utf-8")
    assert 'PYTHON_VERSION = "3.13.15"' in source
    assert len(source.split('PYTHON_SHA256 = "', 1)[1].split('"', 1)[0]) == 64
    assert "OLLAMA_NO_CLOUD=true" in source
    assert "unset OPENAI_API_KEY GEMINI_API_KEY ANTHROPIC_API_KEY" in source
    assert "/usr/bin/python3" not in source


def test_built_archive_contains_complete_runtime_when_present() -> None:
    archive_path = ROOT / "dist" / "aion-sovereign-brain-offline-macos-arm64-0.15.0.zip"
    if not archive_path.is_file():
        return
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        required_suffixes = (
            "offline-python/python/bin/python3",
            "offline-runtime/ollama",
            "offline-runtime/OLLAMA-LICENSE.txt",
            "offline-local-proof.py",
            "offline-verify.py",
            "offline-integrity-manifest.json",
            "requirements-offline-macos-arm64-py313.txt",
        )
        for suffix in required_suffixes:
            assert any(name.endswith(suffix) for name in names), suffix
        manifest_name = next(name for name in names if name.endswith("offline-integrity-manifest.json"))
        manifest = json.loads(archive.read(manifest_name))
        assert manifest["network_required_after_download"] is False
        assert manifest["provider_keys_required"] is False
        assert manifest["model"] == "gemma3:1b"


def test_integrity_verifier_rejects_changed_file(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("offline_verify", PACKAGING / "offline-verify.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    candidate = tmp_path / "item"
    candidate.write_text("trusted", encoding="utf-8")
    original = module.digest(candidate)
    candidate.write_text("changed", encoding="utf-8")
    assert module.digest(candidate) != original
