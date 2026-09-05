from __future__ import annotations

import json
from pathlib import Path

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash
from backend.modules.aion_fabric.identity import DeviceIdentity


def test_production_lock_is_hashed_and_excludes_legacy_feature_stacks():
    value = Path("requirements-production.lock").read_text(encoding="utf-8")
    assert "--hash=sha256:" in value
    assert "cryptography==50.0.0" in value
    assert "keyring==25.7.0" in value
    assert "ecdsa==" not in value
    assert "weasyprint==" not in value


def test_signed_cyclonedx_record_matches_production_lock():
    document = json.loads(Path("dist/release-evidence/aion-flow-production-sbom.cdx.json").read_text())
    evidence = json.loads(Path("dist/release-evidence/aion-flow-production-sbom.signature.json").read_text())
    signature = evidence.pop("signature")
    assert document["bomFormat"] == "CycloneDX"
    assert evidence["artifact_hash"] == canonical_hash(document)
    assert DeviceIdentity.verify(evidence["signer_public_key"], canonical_bytes(evidence), signature)
    names = {item["name"].lower() for item in document["components"]}
    assert "ecdsa" not in names and "weasyprint" not in names
