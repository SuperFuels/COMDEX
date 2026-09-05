from __future__ import annotations

import json
import subprocess
import tarfile
import zipfile

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


def test_linux_installer_and_service_have_safe_static_contract():
    from scripts.build_aion_sovereign_brain_cross_platform_packages import PACKAGING
    installer = PACKAGING / "install-pilot-linux.sh"
    subprocess.run(["sh", "-n", str(installer)], check=True)
    unit = (PACKAGING / "pilot-aion-brain.service").read_text()
    assert "NoNewPrivileges=true" in unit
    assert "ProtectSystem=strict" in unit
    assert "127.0.0.1" not in unit or "--port 8776" in unit
    assert "ReadWritePaths=/var/lib/tessaris/pilot-brain" in unit


def test_windows_service_is_loopback_and_installer_uses_program_data():
    from scripts.build_aion_sovereign_brain_cross_platform_packages import PACKAGING
    installer = (PACKAGING / "Install-Pilot-Windows.ps1").read_text()
    assert "ProgramData" in installer
    assert "WindowsBuiltInRole]::Administrator" in installer
    assert "TessarisPilotBrain" in (PACKAGING.parent.parent / "backend/modules/aion_business/runtime/sovereign_windows_service.py").read_text()
