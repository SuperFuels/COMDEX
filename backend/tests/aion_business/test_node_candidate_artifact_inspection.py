from __future__ import annotations

import gzip
import io
import json
import tarfile
import zipfile

import pytest

from backend.modules.aion_business.runtime.node_candidate_artifact_inspection import (
    NodeCandidateArtifactInspectionError,
    inspect_node_candidate_archive,
)


def _manifest(target: str) -> bytes:
    return json.dumps({
        "clean_machine_validated": False,
        "contains_customer_data": False,
        "network": "loopback-only",
        "platform": target,
        "publisher_signature": False,
        "service": "native-service",
        "status": "developer-preview-unsigned-unqualified",
    }).encode()


def test_windows_candidate_is_inspected_without_extraction(tmp_path):
    candidate = tmp_path / "candidate.zip"
    with zipfile.ZipFile(candidate, "w") as archive:
        archive.writestr("candidate/Install-Pilot-Windows.ps1", "safe")
        archive.writestr("candidate/platform-manifest.json", _manifest("windows-x64"))
        archive.writestr("candidate/payload/app.py", "safe")
    result = inspect_node_candidate_archive(candidate, target_id="windows-x64")
    assert result["passed"] is True
    assert result["unsafe_member_count"] == 0


def test_windows_candidate_rejects_traversal(tmp_path):
    candidate = tmp_path / "bad.zip"
    with zipfile.ZipFile(candidate, "w") as archive:
        archive.writestr("../outside", "unsafe")
    with pytest.raises(NodeCandidateArtifactInspectionError, match="path_unsafe"):
        inspect_node_candidate_archive(candidate, target_id="windows-x64")


def test_linux_candidate_requires_normalized_regular_members(tmp_path):
    candidate = tmp_path / "candidate.tar.gz"
    with candidate.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for name, data, mode in (
                    ("candidate/install-pilot-linux.sh", b"safe", 0o755),
                    ("candidate/pilot-aion-brain.service", b"safe", 0o644),
                    ("candidate/platform-manifest.json", _manifest("linux-x64"), 0o644),
                ):
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    info.mode = mode
                    info.uid = info.gid = info.mtime = 0
                    archive.addfile(info, io.BytesIO(data))
    result = inspect_node_candidate_archive(candidate, target_id="linux-x64")
    assert result["passed"] is True


def test_linux_candidate_rejects_links(tmp_path):
    candidate = tmp_path / "bad.tar.gz"
    with tarfile.open(candidate, "w:gz") as archive:
        info = tarfile.TarInfo("candidate/link")
        info.type = tarfile.SYMTYPE
        info.linkname = "/tmp/outside"
        archive.addfile(info)
    with pytest.raises(NodeCandidateArtifactInspectionError, match="special_member"):
        inspect_node_candidate_archive(candidate, target_id="linux-x64")
