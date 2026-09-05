from __future__ import annotations

import hashlib
import json
import os
import subprocess
import zipfile
from pathlib import Path

from scripts.build_aion_sovereign_brain_bootstrap import PACKAGING, build


def test_bootstrap_release_manifest_is_honest_and_provider_free():
    manifest = json.loads((PACKAGING / "release_manifest.json").read_text(encoding="utf-8"))
    assert manifest["network_binding"] == "localhost-only setup service"
    assert manifest["provider_keys_required"] is False
    assert manifest["demo_data_included"] is False
    assert manifest["customer_data_included"] is False
    assert manifest["status"] == "developer-preview-unsigned"
    assert manifest["installer_code_signing"] == "external release gate"


def test_bootstrap_package_has_three_launchers_and_verified_contents(tmp_path, monkeypatch):
    import scripts.build_aion_sovereign_brain_bootstrap as builder

    monkeypatch.setattr(builder, "DIST", tmp_path / "dist")
    package = builder.build()
    with zipfile.ZipFile(package) as archive:
        names = archive.namelist()
        root = names[0].split("/", 1)[0]
        assert f"{root}/Set Up Pilot.command" in names
        assert f"{root}/Set-Up-Pilot.ps1" in names
        assert f"{root}/set-up-pilot.sh" in names
        for runtime_source in (
            "commercial_adoption_service.py",
            "payment_boundary_service.py",
            "sovereign_capacity_planner.py",
            "sovereign_migration_orchestrator.py",
            "sovereign_installed_service.py",
            "sovereign_windows_service.py",
        ):
            assert any(name.endswith(f"backend/modules/aion_business/runtime/{runtime_source}") for name in names)
        integrity = json.loads(archive.read(f"{root}/integrity-manifest.json"))
        assert integrity["contains_customer_data"] is False
        assert integrity["contains_provider_credentials"] is False
        assert integrity["cryptographic_distribution_signature"] is False
        for record in integrity["files"]:
            raw = archive.read(f"{root}/{record['path']}")
            assert len(raw) == record["bytes"]
            assert hashlib.sha256(raw).hexdigest() == record["sha256"]
        encoded = b"".join(archive.read(name) for name in names)
        assert b"OPENAI_API_KEY=" not in encoded
        assert b"GEMINI_API_KEY=" not in encoded

    extracted = tmp_path / "extracted"
    with zipfile.ZipFile(package) as archive:
        archive.extractall(extracted)
    result = subprocess.run(
        [str(Path(__import__("sys").executable)), "-m", "backend.modules.aion_business.runtime.sovereign_setup_service", "--help"],
        cwd=extracted / root,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "Local Pilot first-run setup" in result.stdout

    offline_root = tmp_path / "offline-brain"
    environment = {
        key: value for key, value in os.environ.items()
        if key not in {"OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"}
    }
    proof = subprocess.run(
        [
            str(Path(__import__("sys").executable)),
            "-c",
            (
                "import json,sys;"
                "from backend.modules.aion_business.runtime.sovereign_brain_setup import SovereignBrainSetup;"
                "print(json.dumps(SovereignBrainSetup(sys.argv[1]).initialize(owner_display_name='Offline Owner')))"
            ),
            str(offline_root),
        ],
        cwd=extracted / root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proof.returncode == 0, proof.stderr
    status = json.loads(proof.stdout)
    assert status["ok"] is True
    assert status["provider_keys_required"] is False
    assert status["demo_data_installed"] is False
