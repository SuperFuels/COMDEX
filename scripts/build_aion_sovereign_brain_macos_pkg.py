#!/usr/bin/env python3
from __future__ import annotations

import json
import plistlib
import shutil
import stat
import subprocess
import tempfile
import zipfile
from pathlib import Path

from scripts.build_aion_sovereign_brain_offline_macos_arm64 import build_offline


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
PACKAGING = ROOT / "packaging" / "aion_sovereign_brain_bootstrap"
IDENTIFIER = "ai.tessaris.aion.brain"
INSTALL_ROOT = Path("Library/Application Support/Tessaris/AION")
LAUNCH_AGENT = "ai.tessaris.aion.brain.plist"


def _executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def build_macos_pkg() -> Path:
    release = json.loads((PACKAGING / "release_manifest.json").read_text(encoding="utf-8"))
    version = str(release["version"])
    offline_archive = build_offline()
    output = DIST / f"Pilot-AION-Brain-macOS-arm64-{version}-unsigned.pkg"
    with tempfile.TemporaryDirectory(prefix="aion-macos-pkg-") as temporary:
        workspace = Path(temporary)
        payload = workspace / "payload"
        installed = payload / INSTALL_ROOT
        installed.mkdir(parents=True)
        with zipfile.ZipFile(offline_archive) as archive:
            archive.extractall(workspace / "offline")
        bundle = next((workspace / "offline").iterdir())
        for source in bundle.iterdir():
            target = installed / source.name
            if source.is_dir():
                shutil.copytree(source, target, symlinks=True)
            else:
                shutil.copy2(source, target)

        app = payload / "Applications/Pilot Setup.app/Contents"
        executable = app / "MacOS/Pilot Setup"
        executable.parent.mkdir(parents=True)
        executable.write_text(
            '#!/bin/zsh\nset -e\nROOT="/Library/Application Support/Tessaris/AION"\n'
            'exec "$ROOT/Set Up Pilot Offline.command"\n',
            encoding="utf-8",
        )
        _executable(executable)
        with (app / "Info.plist").open("wb") as handle:
            plistlib.dump({
                "CFBundleDisplayName": "Pilot Setup",
                "CFBundleExecutable": "Pilot Setup",
                "CFBundleIdentifier": "ai.tessaris.aion.setup",
                "CFBundleInfoDictionaryVersion": "6.0",
                "CFBundleName": "Pilot Setup",
                "CFBundlePackageType": "APPL",
                "CFBundleShortVersionString": version,
                "CFBundleVersion": version.replace(".", ""),
                "LSMinimumSystemVersion": "13.0",
                "LSUIElement": False,
            }, handle, sort_keys=True)

        launch_agents = payload / "Library/LaunchAgents"
        launch_agents.mkdir(parents=True)
        service_python = "/Library/Application Support/Tessaris/AION/offline-python/python/bin/python3"
        with (launch_agents / LAUNCH_AGENT).open("wb") as handle:
            plistlib.dump({
                "Label": IDENTIFIER,
                "ProgramArguments": [
                    service_python,
                    "-m", "backend.modules.aion_business.runtime.sovereign_installed_service",
                    "--port", "8776",
                ],
                "WorkingDirectory": "/Library/Application Support/Tessaris/AION",
                "RunAtLoad": True,
                "KeepAlive": {"SuccessfulExit": False},
                "ThrottleInterval": 10,
                "ProcessType": "Background",
                "EnvironmentVariables": {"PYTHONDONTWRITEBYTECODE": "1"},
                "StandardOutPath": "/tmp/ai.tessaris.aion.brain.stdout.log",
                "StandardErrorPath": "/tmp/ai.tessaris.aion.brain.stderr.log",
            }, handle, sort_keys=True)

        scripts = workspace / "scripts"
        scripts.mkdir()
        postinstall = scripts / "postinstall"
        postinstall.write_text(
            "#!/bin/zsh\nset -e\n"
            "chmod 755 '/Library/Application Support/Tessaris/AION/offline-python/python/bin/python3'\n"
            "chmod 755 '/Library/Application Support/Tessaris/AION/offline-runtime/ollama'\n"
            "chmod 755 '/Library/Application Support/Tessaris/AION/Set Up Pilot Offline.command'\n"
            "exit 0\n",
            encoding="utf-8",
        )
        _executable(postinstall)
        subprocess.run([
            "/usr/bin/pkgbuild",
            "--root", str(payload),
            "--scripts", str(scripts),
            "--identifier", IDENTIFIER,
            "--version", version,
            "--install-location", "/",
            str(output),
        ], check=True)
    return output


if __name__ == "__main__":
    print(build_macos_pkg())
