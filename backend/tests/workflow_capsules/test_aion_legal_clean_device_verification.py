from __future__ import annotations

import base64
from hashlib import sha256
import io
import json
from pathlib import Path
import zipfile

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from backend.modules.aion_business.runtime.legal_clean_device_verification import (
    CleanDeviceVerificationError,
    verify_clean_device_package,
    verify_clean_device_report,
    write_clean_device_report,
)
from backend.modules.aion_business.runtime.legal_document_proof import (
    LegalDocumentProofService,
    _canonical,
    _digest,
    _signature_commitments,
)
from backend.modules.chain_sim.chain_sim_merkle import hash_leaf
from backend.modules.chain_sim.document_proof import (
    DOCUMENT_PROOF_SCHEMA,
    DOCUMENT_PROOF_VERIFICATION_VERSION,
)
from backend.modules.consensus.finality_certificate import (
    build_finality_certificate,
    vote_sign_bytes,
)
from backend.modules.consensus.finality_checkpoint import CHECKPOINT_SCHEMA, normalize_checkpoint
from backend.modules.consensus.trust_release import build_trust_release


ROOT = Path(__file__).resolve().parents[3]


def _fixture(tmp_path):
    document = "Exact clean-device agreement"
    document_hash = sha256(document.encode()).hexdigest()
    signers = [{
        "signer_id": "signer-1",
        "name": "Private Person",
        "email": "private@example.com",
        "signed_at": "2026-09-27T10:00:00Z",
        "signature_method": "typed_name_email",
        "accepted_document_hash": document_hash,
    }]
    payload = {
        "schema_version": DOCUMENT_PROOF_SCHEMA,
        "proof_id": "proof-clean-device-001",
        "document_id_commitment": "11" * 32,
        "document_hash": document_hash,
        "signed_copy_hash": "22" * 32,
        "signatures_root": _digest(_signature_commitments(signers)),
        "audit_root": "33" * 32,
        "issuer_key_id": "ed25519:clean-device-origin",
        "completed_at_ms": 1_798_768_800_000,
        "policy_version": LegalDocumentProofService.POLICY_VERSION,
        "verification_version": DOCUMENT_PROOF_VERIFICATION_VERSION,
    }

    validator_keys = [Ed25519PrivateKey.generate() for _ in range(3)]
    validators = [{
        "validator_id": f"validator-{index + 1}",
        "power": 1,
        "public_key_base64": base64.b64encode(key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )).decode(),
    } for index, key in enumerate(validator_keys)]
    checkpoint = normalize_checkpoint({
        "schema_version": CHECKPOINT_SCHEMA,
        "chain_id": "glyphchain-clean-test",
        "network_id": "clean-testnet",
        "epoch": 0,
        "effective_height": 1,
        "validator_set": validators,
    })
    checkpoint_path = tmp_path / "checkpoint.json"
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")

    envelope = {
        "from_addr": "glyph1cleanorigin",
        "nonce": 1,
        "tx_type": "DOCUMENT_PROOF_V1",
        "payload": payload,
    }
    tx_hash = sha256(_canonical(envelope)).hexdigest()
    txs_root = hash_leaf(bytes.fromhex(tx_hash)).hex()
    ledger_commitment = "44" * 32
    block_id = f"block-9-C{ledger_commitment}"
    certificate = build_finality_certificate(
        chain_id="glyphchain-clean-test",
        network_id="clean-testnet",
        height=9,
        round=1,
        block_id=block_id,
        validator_set=validators,
        votes=[],
        checkpoint_id=checkpoint["checkpoint_id"],
        ledger_commitment=ledger_commitment,
        txs_root=txs_root,
    )
    certificate["votes"] = [{
        "validator_id": validators[index]["validator_id"],
        "signature_base64": base64.b64encode(
            validator_keys[index].sign(
                vote_sign_bytes(certificate, validators[index]["validator_id"])
            )
        ).decode(),
    } for index in (0, 1)]

    origin_key = Ed25519PrivateKey.generate()
    attestation = {
        "receipt_version": LegalDocumentProofService.RECEIPT_VERSION,
        "created_at": "2026-09-27T10:01:00Z",
        "glyphchain_payload": payload,
        "chain_context": {
            "network": "GlyphChain",
            "chain_id": "glyphchain-clean-test",
            "network_id": "clean-testnet",
            "protocol_version": LegalDocumentProofService.PROTOCOL_VERSION,
            "transaction_hash_version": LegalDocumentProofService.TRANSACTION_HASH_VERSION,
        },
        "origin_device": {
            "algorithm": "ed25519",
            "key_id": "ed25519:clean-device-origin",
            "key_version": 1,
            "public_key_base64": base64.b64encode(origin_key.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw,
            )).decode(),
        },
    }
    proof = {
        **attestation,
        "device_signature_base64": base64.b64encode(
            origin_key.sign(_canonical(attestation))
        ).decode(),
        "glyphchain": {
            "status": "FINALIZED",
            "tx_id": f"tx_{tx_hash[:12]}",
            "tx_hash": tx_hash,
            "block_height": 9,
            "block_id": block_id,
            "ledger_commitment": ledger_commitment,
            "txs_root": txs_root,
            "proof": [],
            "transaction_envelope": envelope,
            "quorum_finality_certificate": certificate,
        },
    }
    package = tmp_path / "private-evidence.zip"
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("document.txt", document)
        archive.writestr("envelope.tessaris-proof", json.dumps(proof))
        archive.writestr("evidence-certificate.json", json.dumps({"signers": signers}))

    trust_release = tmp_path / "public-trust-release"
    build_trust_release(
        checkpoint_path=checkpoint_path,
        verifier_path=(
            ROOT / "backend/modules/aion_business/static/tessaris-proof-verifier.html"
        ),
        output_directory=trust_release,
        release_version="2026.09.27-clean-test",
        release_manifest_sha256="55" * 32,
        created_at="2026-09-27T10:02:00Z",
    )
    return package, trust_release, checkpoint


def test_clean_device_verification_is_trust_anchored_and_content_free(tmp_path):
    package, release, checkpoint = _fixture(tmp_path)
    report = verify_clean_device_package(
        evidence_package=package,
        trust_release_directory=release,
        expected_checkpoint_id=checkpoint["checkpoint_id"],
        expected_release_manifest_sha256="55" * 32,
    )
    assert report["valid"] is True
    assert report["result"] == "PASS"
    assert all(report["checks"].values())
    assert report["trust_release"]["trust_anchor_source"] == (
        "independently_supplied_checkpoint_id"
    )
    assert verify_clean_device_report(report) is True
    rendered = json.dumps(report)
    assert "Private Person" not in rendered
    assert "private@example.com" not in rendered
    assert "Exact clean-device agreement" not in rendered


def test_clean_device_verification_detects_document_substitution(tmp_path):
    package, release, checkpoint = _fixture(tmp_path)
    content = io.BytesIO()
    with zipfile.ZipFile(package) as source, zipfile.ZipFile(content, "w") as target:
        for name in source.namelist():
            value = source.read(name)
            target.writestr(name, b"substituted" if name == "document.txt" else value)
    package.write_bytes(content.getvalue())
    report = verify_clean_device_package(
        evidence_package=package,
        trust_release_directory=release,
        expected_checkpoint_id=checkpoint["checkpoint_id"],
    )
    assert report["valid"] is False
    assert report["checks"]["document_matches"] is False
    assert report["errors"]


def test_clean_device_verification_rejects_untrusted_checkpoint(tmp_path):
    package, release, _checkpoint = _fixture(tmp_path)
    with pytest.raises(Exception, match="trusted_checkpoint_id_mismatch"):
        verify_clean_device_package(
            evidence_package=package,
            trust_release_directory=release,
            expected_checkpoint_id="00" * 32,
        )


def test_clean_device_verification_rejects_archive_path_escape(tmp_path):
    package, release, checkpoint = _fixture(tmp_path)
    with zipfile.ZipFile(package, "a") as archive:
        archive.writestr("../escape.txt", "not allowed")
    with pytest.raises(
        CleanDeviceVerificationError, match="clean_device_evidence_member_path_invalid",
    ):
        verify_clean_device_package(
            evidence_package=package,
            trust_release_directory=release,
            expected_checkpoint_id=checkpoint["checkpoint_id"],
        )


def test_clean_device_report_is_exclusive_and_tamper_evident(tmp_path):
    package, release, checkpoint = _fixture(tmp_path)
    report = verify_clean_device_package(
        evidence_package=package,
        trust_release_directory=release,
        expected_checkpoint_id=checkpoint["checkpoint_id"],
    )
    output = write_clean_device_report(tmp_path / "verification.json", report)
    loaded = json.loads(output.read_text())
    assert verify_clean_device_report(loaded) is True
    loaded["result"] = "FAIL"
    assert verify_clean_device_report(loaded) is False
    with pytest.raises(CleanDeviceVerificationError, match="clean_device_report_already_exists"):
        write_clean_device_report(output, report)
