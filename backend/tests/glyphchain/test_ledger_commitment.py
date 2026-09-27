from __future__ import annotations

from copy import deepcopy

import pytest

from backend.modules.chain_sim.chain_sim_ledger import compute_tx_identity
from backend.modules.consensus.ledger_commitment import normalize_ledger_block


def _block() -> dict:
    envelope = {
        "from_addr": "glyph1legalproof",
        "nonce": 1,
        "tx_type": "DOCUMENT_PROOF_V1",
        "payload": {"proof_id": "proof-1", "document_hash": "ab" * 32},
    }
    tx_id, tx_hash = compute_tx_identity(**envelope)
    return {
        "height": 7,
        "txs": [{**envelope, "tx_id": tx_id, "tx_hash": tx_hash, "tx_index": 0}],
        "header": {},
    }


def test_ledger_commitment_binds_exact_transaction_envelope_and_merkle_root():
    block = _block()
    result = normalize_ledger_block(block, chain_id="glyphchain-test", height=7)
    assert len(result["ledger_commitment"]) == 64
    assert len(result["txs_root"]) == 64
    assert result["commitment_payload"]["transactions"][0]["tx_id"].startswith("tx_")

    changed = deepcopy(block)
    changed["txs"][0]["payload"]["document_hash"] = "cd" * 32
    with pytest.raises(ValueError, match="ledger_transaction_envelope_mismatch"):
        normalize_ledger_block(changed, chain_id="glyphchain-test", height=7)


def test_ledger_commitment_rejects_declared_root_not_matching_transaction_order():
    block = _block()
    block["txs_root"] = "00" * 32
    with pytest.raises(ValueError, match="ledger_txs_root_mismatch"):
        normalize_ledger_block(block, chain_id="glyphchain-test", height=7)
