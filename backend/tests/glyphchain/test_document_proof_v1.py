from __future__ import annotations

import json

import pytest

from backend.modules.chain_sim import chain_sim_model as bank
from backend.modules.chain_sim.chain_sim_ledger import find_document_proof_tx, reset_ledger
from backend.modules.chain_sim.chain_sim_merkle import hash_leaf, verify_proof
from backend.modules.chain_sim.chain_sim_routes import (
    DevSubmitTx,
    _submit_tx_sync_block,
    _tx_inclusion_proof,
)
from backend.modules.chain_sim.document_proof import (
    DOCUMENT_PROOF_SCHEMA,
    DOCUMENT_PROOF_VERIFICATION_VERSION,
    DocumentProofValidationError,
    normalize_document_proof_payload,
)


def _hash(character: str) -> str:
    return character * 64


def _payload() -> dict:
    return {
        "schema_version": DOCUMENT_PROOF_SCHEMA,
        "proof_id": "proof-env-001-v1",
        "document_id_commitment": _hash("1"),
        "document_hash": _hash("2"),
        "signed_copy_hash": _hash("3"),
        "signatures_root": _hash("4"),
        "audit_root": _hash("5"),
        "issuer_key_id": "ed25519:device-key-001",
        "completed_at_ms": 1_798_768_800_000,
        "policy_version": "tessaris-signing-policy-v1",
        "verification_version": DOCUMENT_PROOF_VERIFICATION_VERSION,
    }


@pytest.fixture(autouse=True)
def _isolated_chain(monkeypatch):
    monkeypatch.setenv("CHAIN_SIM_PERSIST", "0")
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "off")
    reset_ledger(clear_persist=False)
    bank.reset_state()
    yield
    reset_ledger(clear_persist=False)
    bank.reset_state()


def test_document_proof_payload_is_canonical_and_commitment_only():
    assert normalize_document_proof_payload(_payload()) == _payload()


@pytest.mark.parametrize("private_field", ["content", "email", "name", "signature", "token"])
def test_document_proof_rejects_private_or_human_readable_fields(private_field: str):
    payload = _payload()
    payload[private_field] = "must not be public"
    with pytest.raises(DocumentProofValidationError, match="forbidden"):
        normalize_document_proof_payload(payload)


def test_document_proof_rejects_unknown_fields_and_bad_hashes():
    payload = _payload()
    payload["future_unreviewed_field"] = True
    with pytest.raises(DocumentProofValidationError, match="unsupported payload fields"):
        normalize_document_proof_payload(payload)

    payload = _payload()
    payload["document_hash"] = "not-a-hash"
    with pytest.raises(DocumentProofValidationError, match="document_hash"):
        normalize_document_proof_payload(payload)


def test_document_proof_finalizes_without_currency_or_wallet():
    signer = "glyph1-proof-origin-device"
    before = bank.get_account_view(signer)
    response = _submit_tx_sync_block(
        DevSubmitTx(
            chain_id="glyphchain-dev",
            from_addr=signer,
            nonce=1,
            tx_type="DOCUMENT_PROOF_V1",
            payload=_payload(),
        )
    )
    receipt = json.loads(response.body)

    assert receipt["applied"] is True
    assert receipt["tx_id"].startswith("tx_")
    assert receipt["block_height"] == 1
    assert receipt["result"]["would_move_money"] is False
    assert receipt["result"]["would_require_photon"] is False
    assert receipt["result"]["would_require_wallet"] is False
    assert bank.get_account_view(signer)["balances"] == before["balances"]
    assert bank.get_supply_view() == {"PHO": "0", "TESS": "0"}

    stored = find_document_proof_tx(proof_id=_payload()["proof_id"])
    assert stored is not None
    assert stored["payload"] == _payload()

    inclusion = _tx_inclusion_proof(stored)
    leaf = hash_leaf(bytes.fromhex(inclusion["tx_hash"]))
    assert verify_proof(leaf, inclusion["proof"], bytes.fromhex(inclusion["txs_root"])) is True


def test_document_proof_lookup_by_document_hash():
    _submit_tx_sync_block(
        DevSubmitTx(
            chain_id="glyphchain-dev",
            from_addr="glyph1-proof-origin-device",
            nonce=1,
            tx_type="DOCUMENT_PROOF_V1",
            payload=_payload(),
        )
    )
    stored = find_document_proof_tx(document_hash=_payload()["document_hash"])
    assert stored is not None
    assert stored["tx_type"] == "DOCUMENT_PROOF_V1"
