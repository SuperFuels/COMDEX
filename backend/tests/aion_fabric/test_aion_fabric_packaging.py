from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from scripts.build_aion_fabric_preview import PACKAGING, validate_build_root


def test_release_manifest_is_fail_closed():
    manifest = json.loads((PACKAGING / "release_manifest.json").read_text(encoding="utf-8"))
    assert manifest["network_binding"] == "localhost-only"
    assert "credentials and vaults" in manifest["excludes"]
    assert "existing COMDEX runtime data" in manifest["excludes"]


def test_preview_bundle_contains_only_declared_runtime(tmp_path, monkeypatch):
    import scripts.build_aion_fabric_preview as builder

    archive_path = builder.build(output_root=tmp_path)
    assert archive_path.exists()
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
    assert any(name.endswith("backend/modules/aion_fabric/runtime.py") for name in names)
    assert any(name.endswith("backend/modules/aion/providers/ollama_provider.py") for name in names)
    assert any(name.endswith("backend/modules/aion_business/runtime/business_connector_onboarding_service.py") for name in names)
    assert any(name.endswith("backend/modules/aion_business/runtime/sovereign_intelligence_router.py") for name in names)
    assert any(name.endswith("backend/modules/aion_business/contracts/intelligence.py") for name in names)
    assert any(name.endswith("Start AION Fabric.command") for name in names)
    assert any(name.endswith("Install Pilot.command") for name in names)
    assert any(name.endswith("Uninstall Pilot.command") for name in names)
    assert not any("hexcore" in name.lower() for name in names)
    assert not any(".runtime" in name for name in names)
    assert not any("vault/data" in name.lower() for name in names)
    assert not any(name.endswith((".pem", ".key", ".sqlite", ".db")) for name in names)
    assert any(name.endswith("bundle-manifest.json") for name in names)


def test_extracted_preview_imports_without_comdex_checkout(tmp_path, monkeypatch):
    import scripts.build_aion_fabric_preview as builder

    archive_path = builder.build(output_root=tmp_path)
    extract_root = tmp_path / "extracted"
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(extract_root)
    bundle_root = next(extract_root.iterdir())
    completed = subprocess.run(
        [sys.executable, "-m", "backend.modules.aion_fabric.cli", "--help"],
        cwd=bundle_root,
        env={"PATH": ""},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "AION Device Fabric" in completed.stdout


def test_preview_build_root_rejects_app_update_vault_and_runtime_overlap(tmp_path):
    for name in ("application", "updates", "vault", "runtime"):
        protected = tmp_path / name
        with pytest.raises(ValueError, match="overlaps_protected_root"):
            validate_build_root(
                protected / "preview",
                protected_roots=(protected,),
            )


def test_preview_archive_is_deterministic(tmp_path):
    import scripts.build_aion_fabric_preview as builder

    first = builder.build(output_root=tmp_path / "first")
    second = builder.build(output_root=tmp_path / "second")
    assert hashlib.sha256(first.read_bytes()).hexdigest() == hashlib.sha256(
        second.read_bytes()
    ).hexdigest()
