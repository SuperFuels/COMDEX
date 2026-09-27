from __future__ import annotations

import base64
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.consensus.finality_certificate import (
    CERTIFICATE_SCHEMA,
    validator_set_root,
    verify_finality_certificate,
    vote_sign_bytes,
)
from backend.modules.consensus.finality_checkpoint import (
    CHECKPOINT_SCHEMA,
    FinalityCheckpointError,
    load_trusted_checkpoint_from_env,
    normalize_checkpoint,
    verify_public_checkpoint,
    write_public_checkpoint,
)


def _certificate() -> tuple[dict, str]:
    keys = [Ed25519PrivateKey.generate() for _ in range(3)]
    validators = [
        {
            "validator_id": f"validator-{index + 1}",
            "power": 1,
            "public_key_base64": base64.b64encode(key.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw,
            )).decode("ascii"),
        }
        for index, key in enumerate(keys)
    ]
    root = validator_set_root(validators)
    certificate = {
        "schema_version": CERTIFICATE_SCHEMA,
        "chain_id": "glyphchain-test",
        "network_id": "testnet",
        "height": 42,
        "round": 1,
        "block_id": f"block-42-C{'11' * 32}",
        "vote_type": "PRECOMMIT",
        "validator_set": validators,
        "validator_set_root": root,
        "quorum_power": 2,
        "ledger_commitment": "11" * 32,
        "txs_root": "22" * 32,
        "votes": [],
    }
    certificate["votes"] = [
        {
            "validator_id": validators[index]["validator_id"],
            "signature_base64": base64.b64encode(keys[index].sign(
                vote_sign_bytes(certificate, validators[index]["validator_id"])
            )).decode("ascii"),
        }
        for index in (0, 1)
    ]
    return certificate, root


def test_finality_certificate_verifies_membership_signatures_quorum_and_trust_anchor():
    certificate, root = _certificate()
    result = verify_finality_certificate(
        certificate,
        trusted_validator_set_root=root,
        expected_chain_id="glyphchain-test",
        expected_height=42,
        expected_block_id=certificate["block_id"],
    )
    assert result["valid"] is True
    assert result["trust_anchor_verified"] is True
    assert result["signed_power"] == 2
    assert result["required_power"] == 2


def test_finality_certificate_rejects_tampered_vote_and_untrusted_membership():
    certificate, _root = _certificate()
    certificate["votes"][0]["signature_base64"] = base64.b64encode(b"0" * 64).decode("ascii")
    result = verify_finality_certificate(
        certificate,
        trusted_validator_set_root="00" * 32,
        expected_chain_id="glyphchain-test",
        expected_height=42,
        expected_block_id=certificate["block_id"],
    )
    assert result["valid"] is False
    assert "validator_vote_signature_invalid:validator-1" in result["errors"]
    assert "signed_quorum_not_reached" in result["errors"]
    assert "validator_set_trust_anchor_mismatch" in result["errors"]


def test_finality_certificate_rejects_duplicate_votes():
    certificate, root = _certificate()
    certificate["votes"].append(dict(certificate["votes"][0]))
    result = verify_finality_certificate(certificate, trusted_validator_set_root=root)
    assert result["valid"] is False
    assert "duplicate_validator_vote" in result["errors"]


def test_checkpoint_requires_an_out_of_band_pinned_id_or_root(monkeypatch):
    certificate, _root = _certificate()
    raw = {
        "schema_version": CHECKPOINT_SCHEMA,
        "chain_id": certificate["chain_id"],
        "network_id": certificate["network_id"],
        "epoch": 0,
        "effective_height": 1,
        "validator_set": certificate["validator_set"],
    }
    normalized = normalize_checkpoint(raw)
    monkeypatch.setenv("GLYPHCHAIN_FINALITY_CHECKPOINT_JSON", json.dumps(raw))
    monkeypatch.delenv("GLYPHCHAIN_FINALITY_CHECKPOINT_PATH", raising=False)
    monkeypatch.delenv("GLYPHCHAIN_TRUSTED_CHECKPOINT_ID", raising=False)
    monkeypatch.delenv("GLYPHCHAIN_TRUSTED_VALIDATOR_SET_ROOT", raising=False)
    try:
        load_trusted_checkpoint_from_env()
        assert False, "an unpinned checkpoint must not become a trust anchor"
    except FinalityCheckpointError as exc:
        assert str(exc) == "checkpoint_requires_pinned_id_or_validator_set_root"

    monkeypatch.setenv("GLYPHCHAIN_TRUSTED_CHECKPOINT_ID", normalized["checkpoint_id"])
    loaded = load_trusted_checkpoint_from_env()
    assert loaded is not None
    assert loaded.checkpoint_id == normalized["checkpoint_id"]
    assert loaded.validator_set_root == normalized["validator_set_root"]


def test_public_checkpoint_export_requires_a_separately_supplied_pin(tmp_path):
    certificate, _root = _certificate()
    raw = {
        "schema_version": CHECKPOINT_SCHEMA,
        "chain_id": certificate["chain_id"],
        "network_id": certificate["network_id"],
        "epoch": 0,
        "effective_height": 1,
        "validator_set": certificate["validator_set"],
    }
    normalized = normalize_checkpoint(raw)
    path = write_public_checkpoint(raw, tmp_path / "validator-set.glyphchain-checkpoint")
    assert json.loads(path.read_text())["checkpoint_id"] == normalized["checkpoint_id"]

    try:
        verify_public_checkpoint(path)
        assert False, "a downloaded checkpoint must not appoint its own trust pin"
    except FinalityCheckpointError as exc:
        assert str(exc) == "checkpoint_verification_requires_independent_pin"

    verified = verify_public_checkpoint(path, expected_checkpoint_id=normalized["checkpoint_id"])
    assert verified["validator_set_root"] == normalized["validator_set_root"]

    try:
        verify_public_checkpoint(path, expected_checkpoint_id="00" * 32)
        assert False, "a mismatched pin must fail"
    except FinalityCheckpointError as exc:
        assert str(exc) == "trusted_checkpoint_id_mismatch"
