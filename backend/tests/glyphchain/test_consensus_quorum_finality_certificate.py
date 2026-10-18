from __future__ import annotations

import base64
import json
import pytest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.consensus.engine import ConsensusEngine
from backend.modules.consensus.finality_certificate import (
    verify_finality_certificate,
    vote_sign_bytes,
)
from backend.modules.consensus.finality_checkpoint import CHECKPOINT_SCHEMA, normalize_checkpoint
from backend.modules.consensus.ledger_commitment import empty_ledger_block, normalize_ledger_block
from backend.modules.consensus.types import Proposal, Vote


def _configure(monkeypatch, tmp_path):
    keys = [Ed25519PrivateKey.generate() for _ in range(3)]
    validators = [
        {
            "validator_id": f"val-{index + 1}",
            "power": 1,
            "public_key_base64": base64.b64encode(key.public_key().public_bytes(
                serialization.Encoding.Raw,
                serialization.PublicFormat.Raw,
            )).decode("ascii"),
        }
        for index, key in enumerate(keys)
    ]
    raw = {
        "schema_version": CHECKPOINT_SCHEMA,
        "chain_id": "glyphchain-certificate-test",
        "network_id": "testnet",
        "epoch": 0,
        "effective_height": 1,
        "validator_set": validators,
    }
    checkpoint = normalize_checkpoint(raw)
    monkeypatch.setenv("GLYPHCHAIN_CHAIN_ID", raw["chain_id"])
    monkeypatch.setenv("GLYPHCHAIN_NETWORK_ID", raw["network_id"])
    monkeypatch.setenv("GLYPHCHAIN_VALIDATORS", "val-1:1,val-2:1,val-3:1")
    monkeypatch.setenv("GLYPHCHAIN_SELF_VAL_ID", "val-1")
    monkeypatch.setenv("GLYPHCHAIN_FINALITY_CHECKPOINT_JSON", json.dumps(raw))
    monkeypatch.setenv("GLYPHCHAIN_TRUSTED_CHECKPOINT_ID", checkpoint["checkpoint_id"])
    monkeypatch.setenv(
        "GLYPHCHAIN_FINALITY_PRIVKEY_HEX",
        keys[0].private_bytes_raw().hex(),
    )
    monkeypatch.setenv("GLYPHCHAIN_STATE_DIR", str(tmp_path / "consensus"))
    monkeypatch.setenv("GLYPHCHAIN_LEDGER_DB_PATH", str(tmp_path / "ledger.sqlite3"))
    return keys, checkpoint


def _signed_precommit(engine, key, validator_id: str, block_id: str) -> Vote:
    proposal = engine._proposals[(1, 0)]
    context = engine._finality_certificate_context(
        height=1,
        round=0,
        block_id=block_id,
        ledger_commitment=proposal.ledger_commitment,
        txs_root=proposal.txs_root,
    )
    return Vote(
        height=1,
        round=0,
        voter=validator_id,
        vote_type="PRECOMMIT",
        block_id=block_id,
        finality_signature_base64=base64.b64encode(
            key.sign(vote_sign_bytes(context, validator_id))
        ).decode("ascii"),
        finality_validator_set_root=engine._finality_checkpoint.validator_set_root,
        finality_checkpoint_id=engine._finality_checkpoint.checkpoint_id,
        ledger_commitment=proposal.ledger_commitment,
        txs_root=proposal.txs_root,
    )


def _install_proposal(engine: ConsensusEngine) -> str:
    block = empty_ledger_block(height=1)
    commitment = normalize_ledger_block(block, chain_id=engine.chain_id, height=1)
    block_id = f"h1-r0-P{engine.leader_for(1, 0)}-C{commitment['ledger_commitment']}"
    result = engine.handle_proposal(Proposal(
        height=1,
        round=0,
        proposer=str(engine.leader_for(1, 0)),
        block_id=block_id,
        block=block,
        ledger_commitment=commitment["ledger_commitment"],
        txs_root=commitment["txs_root"],
    ))
    assert result["ok"] is True
    return block_id


def test_live_consensus_emits_and_persists_independently_verifiable_certificate(monkeypatch, tmp_path):
    keys, checkpoint = _configure(monkeypatch, tmp_path)
    engine = ConsensusEngine()
    monkeypatch.setattr(engine, "_persist_finalized_block_shell", lambda **_kwargs: None)
    block_id = _install_proposal(engine)
    proposal = engine._proposals[(1, 0)]

    missing = engine.handle_vote(Vote(
        height=1,
        round=0,
        voter="val-1",
        vote_type="PRECOMMIT",
        block_id=block_id,
        ledger_commitment=proposal.ledger_commitment,
        txs_root=proposal.txs_root,
    ))
    assert missing["ok"] is False
    assert "finality signature" in missing["error"]

    first = engine.handle_vote(_signed_precommit(engine, keys[0], "val-1", block_id))
    assert first["finalized"] is False
    second = engine.handle_vote(_signed_precommit(engine, keys[1], "val-2", block_id))
    assert second["finalized"] is True
    certificate = second["quorum_finality_certificate"]
    assert certificate["validator_set_checkpoint_id"] == checkpoint["checkpoint_id"]
    assert certificate["ledger_commitment"] == proposal.ledger_commitment
    assert certificate["txs_root"] == proposal.txs_root
    verification = verify_finality_certificate(
        certificate,
        trusted_validator_set_root=checkpoint["validator_set_root"],
        expected_chain_id="glyphchain-certificate-test",
        expected_height=1,
        expected_block_id=block_id,
        expected_ledger_commitment=proposal.ledger_commitment,
        expected_txs_root=proposal.txs_root,
    )
    assert verification["valid"] is True
    assert verification["trust_anchor_verified"] is True
    assert second["qc"]["quorum_finality_certificate"] == certificate
    retained = engine.finality_receipt(height=1, block_id=block_id)
    assert retained["found"] is True
    assert retained["independently_verifiable"] is True
    assert retained["quorum_finality_certificate"] == certificate

    restarted = ConsensusEngine()
    status = restarted.status()
    assert status["finalized_height"] == 1
    assert status["quorum_finality"]["latest_certificate"] == certificate


def test_consensus_rejects_precommit_signed_by_wrong_validator_key(monkeypatch, tmp_path):
    keys, _checkpoint = _configure(monkeypatch, tmp_path)
    engine = ConsensusEngine()
    block_id = _install_proposal(engine)
    vote = _signed_precommit(engine, keys[1], "val-1", block_id)
    result = engine.handle_vote(vote)
    assert result == {"ok": False, "error": "precommit finality signature invalid"}


def test_validator_finality_key_must_not_reuse_p2p_transport_key(monkeypatch, tmp_path):
    keys, _checkpoint = _configure(monkeypatch, tmp_path)
    reused = keys[0].private_bytes_raw().hex()
    monkeypatch.setenv("GLYPHCHAIN_FINALITY_PRIVKEY_HEX", reused)
    monkeypatch.setenv("GLYPHCHAIN_P2P_PRIVKEY_HEX", reused)
    with pytest.raises(ValueError, match="finality and P2P transport keys must be distinct"):
        ConsensusEngine()
