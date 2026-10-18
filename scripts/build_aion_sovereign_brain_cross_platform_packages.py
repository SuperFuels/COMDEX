#!/usr/bin/env python3
"""Build unsigned Windows/Linux developer installer payloads from the sealed bootstrap."""

from __future__ import annotations

import hashlib
import gzip
import json
import shutil
import stat
import tarfile
import tempfile
import zipfile
from pathlib import Path

from scripts.build_aion_sovereign_brain_bootstrap import (
    DIST,
    PACKAGING,
    build,
    write_reproducible_zip_file,
)


def _sha(path: Path) -> str:
    digest = hashlib.sha256(); digest.update(path.read_bytes()); return digest.hexdigest()


def _normalized_tar_info(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    return info


def build_cross_platform() -> dict:
    bootstrap = build()
    release = json.loads((PACKAGING / "release_manifest.json").read_text())
    version = release["version"]
    DIST.mkdir(parents=True, exist_ok=True)
    outputs = {}
    with tempfile.TemporaryDirectory(prefix="aion-cross-platform-") as temporary:
        root = Path(temporary)
        extracted = root / "bootstrap"
        with zipfile.ZipFile(bootstrap) as archive: archive.extractall(extracted)
        payload_source = next(extracted.iterdir())

        windows = root / f"Pilot AION Brain Windows {version}"
        (windows / "payload").mkdir(parents=True)
        shutil.copytree(payload_source, windows / "payload", dirs_exist_ok=True)
        shutil.copy2(PACKAGING / "requirements-windows.txt", windows / "payload/requirements-windows.txt")
        shutil.copy2(PACKAGING / "Install-Pilot-Windows.ps1", windows / "Install-Pilot-Windows.ps1")
        windows_meta = {"platform": "windows-x64", "status": "developer-preview-unsigned-unqualified",
                        "service": "Windows Service Control Manager/TessarisPilotBrain",
                        "network": "loopback-only", "clean_machine_validated": False,
                        "publisher_signature": False, "contains_customer_data": False}
        (windows / "platform-manifest.json").write_text(json.dumps(windows_meta, indent=2, sort_keys=True))
        windows_output = DIST / f"Pilot-AION-Brain-Windows-x64-{version}-unsigned.zip"
        with zipfile.ZipFile(
            windows_output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for path in sorted(windows.rglob("*")):
                if path.is_file():
                    write_reproducible_zip_file(
                        archive,
                        source=path,
                        archive_name=path.relative_to(windows.parent),
                    )
        outputs["windows"] = windows_output

        linux = root / f"pilot-aion-brain-linux-x64-{version}"
        (linux / "payload").mkdir(parents=True)
        shutil.copytree(payload_source, linux / "payload", dirs_exist_ok=True)
        shutil.copy2(PACKAGING / "pilot-aion-brain.service", linux / "pilot-aion-brain.service")
        shutil.copy2(PACKAGING / "install-pilot-linux.sh", linux / "install-pilot-linux.sh")
        (linux / "install-pilot-linux.sh").chmod(0o755)
        linux_meta = {"platform": "linux-x64", "status": "developer-preview-unsigned-unqualified",
                      "service": "systemd/pilot-aion-brain.service", "network": "loopback-only",
                      "clean_machine_validated": False, "publisher_signature": False,
                      "contains_customer_data": False}
        (linux / "platform-manifest.json").write_text(json.dumps(linux_meta, indent=2, sort_keys=True))
        linux_output = DIST / f"pilot-aion-brain-linux-x64-{version}-unsigned.tar.gz"
        with linux_output.open("wb") as raw_output:
            with gzip.GzipFile(fileobj=raw_output, mode="wb", mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode="w") as archive:
                    archive.add(
                        linux,
                        arcname=linux.name,
                        filter=_normalized_tar_info,
                    )
        outputs["linux"] = linux_output

    result = {key: {"path": str(path), "sha256": _sha(path)} for key, path in outputs.items()}
    (DIST / "aion-cross-platform-developer-packages.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    print(json.dumps(build_cross_platform(), indent=2))
