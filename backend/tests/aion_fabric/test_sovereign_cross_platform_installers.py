from __future__ import annotations

import json
import hashlib
import subprocess
import tarfile
import zipfile
from pathlib import Path

from scripts.build_aion_sovereign_brain_cross_platform_packages import build_cross_platform


def test_windows_and_linux_developer_packages_are_honestly_labelled(tmp_path, monkeypatch):
    from scripts import build_aion_sovereign_brain_cross_platform_packages as builder
    monkeypatch.setattr(builder, "DIST", tmp_path)
    result = build_cross_platform()
    with zipfile.ZipFile(result["windows"]["path"]) as archive:
        manifest = json.loads(archive.read(next(name for name in archive.namelist() if name.endswith("platform-manifest.json"))))
        names = archive.namelist()
        assert any(name.endswith("Install-Pilot-Windows.ps1") for name in names)
        assert any(name.endswith("sovereign_windows_service.py") for name in names)
    assert manifest["publisher_signature"] is False
    assert manifest["clean_machine_validated"] is False
    with tarfile.open(result["linux"]["path"], "r:gz") as archive:
        names = archive.getnames()
        assert any(name.endswith("pilot-aion-brain.service") for name in names)
        assert any(name.endswith("install-pilot-linux.sh") for name in names)


def test_windows_and_linux_developer_packages_are_reproducible(tmp_path, monkeypatch):
    from scripts import build_aion_sovereign_brain_cross_platform_packages as builder

    first_dist = tmp_path / "first"
    monkeypatch.setattr(builder, "DIST", first_dist)
    first = builder.build_cross_platform()
    first_hashes = {
        key: hashlib.sha256(Path(result["path"]).read_bytes()).hexdigest()
        for key, result in first.items()
    }
    second_dist = tmp_path / "second"
    monkeypatch.setattr(builder, "DIST", second_dist)
    second = builder.build_cross_platform()
    second_hashes = {
        key: hashlib.sha256(Path(result["path"]).read_bytes()).hexdigest()
        for key, result in second.items()
    }
    assert first_hashes == second_hashes


def test_linux_installer_and_service_have_safe_static_contract():
    from scripts.build_aion_sovereign_brain_cross_platform_packages import PACKAGING
    installer = PACKAGING / "install-pilot-linux.sh"
    subprocess.run(["sh", "-n", str(installer)], check=True)
    unit = (PACKAGING / "pilot-aion-brain.service").read_text()
    assert "NoNewPrivileges=true" in unit
    assert "ProtectSystem=strict" in unit
    assert "--port 0" in unit
    assert "--port 8776" not in unit
    assert "RuntimeDirectory=tessaris-pilot-brain" in unit
    assert "--port-file /run/tessaris-pilot-brain/health-endpoint.json" in unit
    assert "ReadWritePaths=/var/lib/tessaris/pilot-brain /run/tessaris-pilot-brain" in unit


def test_windows_service_is_loopback_and_installer_uses_program_data():
    from scripts.build_aion_sovereign_brain_cross_platform_packages import PACKAGING
    installer = (PACKAGING / "Install-Pilot-Windows.ps1").read_text()
    assert "ProgramData" in installer
    assert "WindowsBuiltInRole]::Administrator" in installer
    assert 'NT SERVICE\\$ServiceName' in installer
    assert "TESSARIS_NODE_STATE_ROOT" in installer
    assert "icacls.exe $InstallRoot" in installer
    assert '${ServiceIdentity}:(OI)(CI)RX' in installer
    assert "icacls.exe $BrainRoot" in installer
    assert '${ServiceIdentity}:(OI)(CI)M' in installer
    service = (PACKAGING.parent.parent / "backend/modules/aion_business/runtime/sovereign_windows_service.py").read_text()
    assert "TessarisPilotBrain" in service
    assert 'host="127.0.0.1"' in service
    assert "port=0" in service
    assert "8776" not in service
