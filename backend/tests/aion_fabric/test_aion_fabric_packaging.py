from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

from scripts.build_aion_fabric_preview import PACKAGING, build


def test_release_manifest_is_fail_closed():
    manifest = json.loads((PACKAGING / "release_manifest.json").read_text(encoding="utf-8"))
    assert manifest["network_binding"] == "localhost-only"
    assert "credentials and vaults" in manifest["excludes"]
    assert "existing COMDEX runtime data" in manifest["excludes"]


def test_preview_bundle_contains_only_declared_runtime(tmp_path, monkeypatch):
    import scripts.build_aion_fabric_preview as builder

    monkeypatch.setattr(builder, "DIST", tmp_path)
    archive_path = builder.build()
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


def test_extracted_preview_imports_without_comdex_checkout(tmp_path, monkeypatch):
    import scripts.build_aion_fabric_preview as builder

    monkeypatch.setattr(builder, "DIST", tmp_path)
    archive_path = builder.build()
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
