from __future__ import annotations

import json
import zipfile

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.aion_business.runtime.sovereign_update_service import (
    SovereignUpdateService,
    build_signed_update_package,
)
from backend.modules.aion_fabric.canonical import canonical_bytes
from backend.modules.aion_fabric.identity import DeviceIdentity


def identity():
    return DeviceIdentity(Ed25519PrivateKey.generate())


def package(tmp_path, publisher, version, content):
    source = tmp_path / f"source-{version}-{__import__('hashlib').sha256(content.encode()).hexdigest()[:8]}"
    source.mkdir()
    (source / "runtime.txt").write_text(content, encoding="utf-8")
    return build_signed_update_package(source, tmp_path / f"{version}.zip", version=version, publisher=publisher)


def test_signed_update_stages_activates_and_retains_receipt_chain(tmp_path):
    publisher, mother = identity(), identity()
    service = SovereignUpdateService(tmp_path / "updates", mother_identity=mother, trusted_signers=[publisher.public_key_b64])
    staged = service.stage(package(tmp_path, publisher, "1.0.0", "healthy"))
    assert staged["status"] == "staged"
    result = service.activate("1.0.0", start_release=lambda path: True, health_check=lambda path: (path / "runtime.txt").read_text() == "healthy")
    assert result["status"] == "activated"
    status = service.status()
    assert status["current_version"] == "1.0.0"
    assert [item["event"] for item in status["history"]] == ["staged", "activated"]
    assert status["history"][1]["previous_hash"] == status["history"][0]["receipt_hash"]


def test_failed_candidate_automatically_rolls_back_to_verified_previous_release(tmp_path):
    publisher, mother = identity(), identity()
    service = SovereignUpdateService(tmp_path / "updates", mother_identity=mother, trusted_signers=[publisher.public_key_b64])
    service.stage(package(tmp_path, publisher, "1.0.0", "healthy"))
    service.activate("1.0.0", start_release=lambda path: True, health_check=lambda path: True)
    service.stage(package(tmp_path, publisher, "2.0.0", "broken"))
    started = []
    result = service.activate(
        "2.0.0",
        start_release=lambda path: started.append(path.name) or True,
        health_check=lambda path: (path / "runtime.txt").read_text() == "healthy",
        stop_release=lambda path: True,
    )
    assert result["status"] == "rolled_back"
    assert result["rolled_back_to"] == "1.0.0"
    assert result["previous_runtime_healthy"] is True
    assert service.status()["current_version"] == "1.0.0"
    assert started == ["2.0.0", "1.0.0"]


def test_untrusted_tampered_and_path_traversal_packages_fail_closed(tmp_path):
    trusted, attacker, mother = identity(), identity(), identity()
    service = SovereignUpdateService(tmp_path / "updates", mother_identity=mother, trusted_signers=[trusted.public_key_b64])
    with pytest.raises(PermissionError, match="signer_not_trusted"):
        service.stage(package(tmp_path, attacker, "1.0.0", "attacker"))

    valid = package(tmp_path, trusted, "1.0.0", "original")
    tampered = tmp_path / "tampered.zip"
    with zipfile.ZipFile(valid) as source, zipfile.ZipFile(tampered, "w") as target:
        for info in source.infolist():
            target.writestr(info.filename, b"changed" if info.filename == "runtime.txt" else source.read(info))
    with pytest.raises(ValueError, match="integrity_failed"):
        service.stage(tampered)

    unsafe = tmp_path / "unsafe.zip"
    raw = b"outside"
    unsigned = {
        "schema_version": "aion.sovereign_update.v1", "version": "3.0.0", "created_at": "now",
        "signer_public_key": trusted.public_key_b64,
        "files": [{"path": "../outside", "bytes": len(raw), "sha256": __import__("hashlib").sha256(raw).hexdigest(), "executable": False}],
        "customer_data_included": False, "customer_credentials_included": False,
    }
    manifest = {**unsigned, "signature": trusted.sign(canonical_bytes(unsigned))}
    with zipfile.ZipFile(unsafe, "w") as archive:
        archive.writestr("update-manifest.json", canonical_bytes(manifest))
        archive.writestr("../outside", raw)
    with pytest.raises(ValueError, match="path_unsafe"):
        service.stage(unsafe)


def test_failed_first_activation_requires_manual_recovery_without_false_success(tmp_path):
    publisher, mother = identity(), identity()
    service = SovereignUpdateService(tmp_path / "updates", mother_identity=mother, trusted_signers=[publisher.public_key_b64])
    service.stage(package(tmp_path, publisher, "1.0.0", "broken"))
    result = service.activate("1.0.0", start_release=lambda path: False, health_check=lambda path: False)
    assert result["status"] == "rolled_back"
    assert result["manual_recovery_required"] is True
    assert service.status()["current_version"] is None
