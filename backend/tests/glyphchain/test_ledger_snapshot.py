from __future__ import annotations

import base64
import json
from pathlib import Path
import sqlite3
import zipfile

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.modules.chain_sim.chain_sim_ledger import (
    compute_tx_identity,
    install_verified_ledger_database,
)
from backend.modules.chain_sim.chain_sim_merkle import hash_leaf, merkle_root
from backend.modules.chain_sim.ledger_snapshot import (
    LedgerSnapshotError,
    export_ledger_snapshot,
    verify_ledger_snapshot,
)
from backend.modules.consensus.finality_certificate import (
    build_finality_certificate,
    vote_sign_bytes,
)
from backend.modules.consensus.finality_checkpoint import (
    CHECKPOINT_SCHEMA,
    TrustedFinalityCheckpoint,
    normalize_checkpoint,
)
from backend.modules.consensus.ledger_commitment import normalize_ledger_block


CHAIN_ID = "glyphchain-snapshot-test"
NETWORK_ID = "snapshotnet"


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _database(path: Path, *, height: int = 1) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        PRAGMA foreign_keys=ON;
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE blocks (
          height INTEGER PRIMARY KEY, created_at_ms INTEGER NOT NULL,
          header_json TEXT NOT NULL, state_root TEXT, txs_root TEXT
        );
        CREATE TABLE txs (
          tx_id TEXT PRIMARY KEY, tx_hash TEXT NOT NULL, block_height INTEGER NOT NULL,
          tx_index INTEGER NOT NULL, from_addr TEXT NOT NULL, nonce INTEGER NOT NULL,
          tx_type TEXT NOT NULL, payload_json TEXT NOT NULL, applied INTEGER NOT NULL,
          result_json TEXT NOT NULL, fee_json TEXT,
          FOREIGN KEY(block_height) REFERENCES blocks(height) ON DELETE CASCADE
        );
        CREATE INDEX idx_txs_block ON txs(block_height, tx_index);
        CREATE INDEX idx_txs_from ON txs(from_addr);
        CREATE INDEX idx_txs_hash ON txs(tx_hash);
        PRAGMA user_version=1;
        """
    )
    payload = {
        "schema_version": "glyphchain.document-proof.v1",
        "proof_id": f"proof-{height}",
        "document_id_commitment": "11" * 32,
        "document_hash": "ab" * 32,
        "signed_copy_hash": "22" * 32,
        "signatures_root": "33" * 32,
        "audit_root": "44" * 32,
        "issuer_key_id": "snapshot-test-key",
        "completed_at_ms": 1_700_000_000_000 + height,
        "policy_version": "snapshot-test-v1",
        "verification_version": "sha256-merkle-ed25519-v1",
    }
    tx_id, tx_hash = compute_tx_identity("origin-device", height, "DOCUMENT_PROOF_V1", payload)
    txs_root = merkle_root([hash_leaf(bytes.fromhex(tx_hash))]).hex()
    state_root = f"{height:064x}"
    header = {"state_root": state_root, "txs_root": txs_root}
    connection.execute(
        "INSERT INTO blocks VALUES(?,?,?,?,?)",
        (height, 1_700_000_000_000 + height, json.dumps(header), state_root, txs_root),
    )
    connection.execute(
        "INSERT INTO txs VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (tx_id, tx_hash, height, 0, "origin-device", height, "DOCUMENT_PROOF_V1",
         json.dumps(payload), 1, json.dumps({"state_root": state_root, "txs_root": txs_root}), None),
    )
    checkpoint = {
        "last_height": height,
        "last_state_root": state_root,
        "last_txs_root": txs_root,
        "updated_at_ms": 1_700_000_000_000 + height,
    }
    connection.execute("INSERT INTO meta VALUES(?,?)", ("checkpoint_json", json.dumps(checkpoint)))
    connection.commit()
    connection.close()
    block = {
        "height": height,
        "created_at_ms": 1_700_000_000_000 + height,
        "header": header,
        "state_root": state_root,
        "txs_root": txs_root,
        "txs": [{
            "tx_id": tx_id, "tx_hash": tx_hash, "tx_index": 0,
            "from_addr": "origin-device", "nonce": height,
            "tx_type": "DOCUMENT_PROOF_V1", "payload": payload,
        }],
    }
    return block


def _trust_and_certificate(block: dict) -> tuple[TrustedFinalityCheckpoint, dict]:
    keys = [Ed25519PrivateKey.generate() for _ in range(3)]
    validators = [{
        "validator_id": f"validator-{index + 1}",
        "power": 1,
        "public_key_base64": base64.b64encode(
            key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        ).decode("ascii"),
    } for index, key in enumerate(keys)]
    checkpoint = normalize_checkpoint({
        "schema_version": CHECKPOINT_SCHEMA,
        "chain_id": CHAIN_ID,
        "network_id": NETWORK_ID,
        "epoch": 0,
        "effective_height": 1,
        "validator_set": validators,
    })
    commitment = normalize_ledger_block(block, chain_id=CHAIN_ID, height=int(block["height"]))
    block_id = f"h{block['height']}-r0-Pvalidator-1-C{commitment['ledger_commitment']}"
    context = build_finality_certificate(
        chain_id=CHAIN_ID, network_id=NETWORK_ID, height=block["height"], round=0,
        block_id=block_id, validator_set=validators, votes=[],
        checkpoint_id=checkpoint["checkpoint_id"],
        ledger_commitment=commitment["ledger_commitment"], txs_root=commitment["txs_root"],
    )
    votes = [{
        "validator_id": validators[index]["validator_id"],
        "signature_base64": base64.b64encode(keys[index].sign(
            vote_sign_bytes(context, validators[index]["validator_id"])
        )).decode("ascii"),
    } for index in range(2)]
    certificate = build_finality_certificate(
        chain_id=CHAIN_ID, network_id=NETWORK_ID, height=block["height"], round=0,
        block_id=block_id, validator_set=validators, votes=votes,
        checkpoint_id=checkpoint["checkpoint_id"],
        ledger_commitment=commitment["ledger_commitment"], txs_root=commitment["txs_root"],
    )
    return TrustedFinalityCheckpoint(checkpoint, "test-pin"), certificate


def _export(tmp_path: Path, *, height: int = 1):
    database = tmp_path / f"source-{height}.sqlite3"
    block = _database(database, height=height)
    trust, certificate = _trust_and_certificate(block)
    snapshot = tmp_path / f"snapshot-{height}.glyphchain-snapshot"
    manifest = export_ledger_snapshot(
        database_path=database, output_path=snapshot, chain_id=CHAIN_ID, network_id=NETWORK_ID,
        finality_certificate=certificate, validator_checkpoint=trust.value,
    )
    return database, snapshot, trust, manifest


def test_snapshot_export_and_independent_verification(tmp_path):
    _database_path, snapshot, trust, manifest = _export(tmp_path)
    verified = verify_ledger_snapshot(
        snapshot, trusted_checkpoint=trust,
        expected_chain_id=CHAIN_ID, expected_network_id=NETWORK_ID,
    )
    try:
        assert verified.summary()["verified"] is True
        assert verified.summary()["snapshot_id"] == manifest["snapshot_id"]
        assert verified.summary()["ledger"]["height"] == 1
    finally:
        verified.cleanup()


def test_snapshot_rejects_database_tampering(tmp_path):
    _database_path, snapshot, trust, _manifest = _export(tmp_path)
    rewritten = tmp_path / "tampered.glyphchain-snapshot"
    with zipfile.ZipFile(snapshot, "r") as source, zipfile.ZipFile(rewritten, "w") as target:
        for info in source.infolist():
            body = source.read(info.filename)
            if info.filename == "ledger.sqlite3":
                body = body[:-1] + bytes([body[-1] ^ 1])
            target.writestr(info.filename, body)
    with pytest.raises(LedgerSnapshotError, match="snapshot_database_digest_mismatch"):
        verify_ledger_snapshot(
            rewritten, trusted_checkpoint=trust,
            expected_chain_id=CHAIN_ID, expected_network_id=NETWORK_ID,
        )


def test_snapshot_rejects_hidden_database_trigger(tmp_path):
    database, _snapshot, trust, _manifest = _export(tmp_path)
    connection = sqlite3.connect(database)
    connection.execute(
        "CREATE TRIGGER hidden_after_insert AFTER INSERT ON txs BEGIN UPDATE meta SET value=value; END"
    )
    connection.commit()
    connection.close()
    unsafe = tmp_path / "unsafe.glyphchain-snapshot"
    # Export performs the same schema validation as import and must fail before
    # producing a transportable archive.
    with pytest.raises(LedgerSnapshotError, match="snapshot_database_active_schema_object_rejected"):
        export_ledger_snapshot(
            database_path=database, output_path=unsafe,
            chain_id=CHAIN_ID, network_id=NETWORK_ID,
            finality_certificate={}, validator_checkpoint=trust.value,
        )


def test_snapshot_rejects_untrusted_bundled_validator_set(tmp_path):
    _database_path, snapshot, _trust, _manifest = _export(tmp_path)
    other_block = _database(tmp_path / "other.sqlite3", height=1)
    other_trust, _certificate = _trust_and_certificate(other_block)
    with pytest.raises(LedgerSnapshotError, match="snapshot_checkpoint_not_independently_trusted"):
        verify_ledger_snapshot(
            snapshot, trusted_checkpoint=other_trust,
            expected_chain_id=CHAIN_ID, expected_network_id=NETWORK_ID,
        )


def test_snapshot_rejects_rollback(tmp_path):
    _database_path, snapshot, trust, _manifest = _export(tmp_path, height=1)
    with pytest.raises(LedgerSnapshotError, match="snapshot_rollback_rejected"):
        verify_ledger_snapshot(
            snapshot, trusted_checkpoint=trust,
            expected_chain_id=CHAIN_ID, expected_network_id=NETWORK_ID,
            minimum_height=2,
        )


def test_verified_snapshot_install_is_atomic_and_retains_previous_database(tmp_path, monkeypatch):
    target = tmp_path / "live.sqlite3"
    _database(target, height=1)
    _database_path, snapshot, trust, _manifest = _export(tmp_path, height=2)
    verified = verify_ledger_snapshot(
        snapshot, trusted_checkpoint=trust,
        expected_chain_id=CHAIN_ID, expected_network_id=NETWORK_ID,
        minimum_height=1,
    )
    monkeypatch.setenv("CHAIN_SIM_PERSIST", "1")
    monkeypatch.setenv("CHAIN_SIM_DB_PATH", str(target))
    monkeypatch.setenv("GLYPHCHAIN_LEDGER_MAX_BYTES", str(64 * 1024 * 1024))
    try:
        result = install_verified_ledger_database(
            verified.database_path,
            expected_sha256=verified.manifest["ledger"]["database_sha256"],
        )
        assert result["installed"] is True
        assert result["backup_retained"] is True
        assert result["restart_required"] is True
        connection = sqlite3.connect(target)
        checkpoint = json.loads(connection.execute(
            "SELECT value FROM meta WHERE key='checkpoint_json'"
        ).fetchone()[0])
        connection.close()
        assert checkpoint["last_height"] == 2
        assert target.with_suffix(target.suffix + ".pre-snapshot").exists()
    finally:
        verified.cleanup()
