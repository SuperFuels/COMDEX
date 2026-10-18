from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import shutil
import sqlite3

import pytest

from backend.modules.chain_sim.canonical_codec import canonical_hash_hex
from backend.modules.chain_sim.chain_sim_config import get_config, set_config
from backend.modules.chain_sim.chain_sim_ledger import (
    compute_tx_identity,
    get_block,
    install_verified_ledger_database,
    record_applied_tx,
)
from backend.modules.chain_sim.chain_sim_merkle import hash_leaf, merkle_root, verify_proof
from backend.modules.chain_sim.ledger_pruning import LedgerPruningError, compact_ledger_copy


@pytest.fixture(autouse=True)
def _preserve_process_chain_identity():
    """The restart test imports a snapshot into process-global chain state."""

    previous = get_config()
    yield
    set_config(
        chain_id=str(previous["chain_id"]),
        network_id=str(previous["network_id"]),
    )


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _state() -> dict:
    return {
        "config": {"chain_id": "glyphchain-prune-test", "network_id": "prunenet"},
        "bank": {"accounts": {}},
        "staking": {"validators": []},
    }


def _database(path: Path) -> tuple[str, str]:
    state_root = canonical_hash_hex(_state())
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
    first_hash = ""
    final_root = ""
    for height in range(1, 4):
        payload = {
            "schema_version": "glyphchain.document-proof.v1",
            "proof_id": f"proof-{height}",
            "document_id_commitment": "11" * 32,
            "document_hash": f"{height:02x}" * 32,
            "signed_copy_hash": "22" * 32,
            "signatures_root": "33" * 32,
            "audit_root": "44" * 32,
            "issuer_key_id": "pruning-test-key",
            "completed_at_ms": 1_700_000_000_000 + height,
            "policy_version": "pruning-test-v1",
            "verification_version": "sha256-merkle-ed25519-v1",
        }
        tx_id, tx_hash = compute_tx_identity("origin-device", height, "DOCUMENT_PROOF_V1", payload)
        root = merkle_root([hash_leaf(bytes.fromhex(tx_hash))]).hex()
        if height == 1:
            first_hash = tx_hash
        final_root = root
        header = {"state_root": state_root, "txs_root": root}
        connection.execute(
            "INSERT INTO blocks VALUES(?,?,?,?,?)",
            (height, 1_700_000_000_000 + height, json.dumps(header), state_root, root),
        )
        connection.execute(
            "INSERT INTO txs VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (tx_id, tx_hash, height, 0, "origin-device", height, "DOCUMENT_PROOF_V1",
             json.dumps(payload), 1, json.dumps({"state_root": state_root, "txs_root": root}), None),
        )
    checkpoint = {
        "last_height": 3,
        "last_state_root": state_root,
        "last_txs_root": final_root,
        "updated_at_ms": 1_700_000_000_003,
    }
    connection.execute("INSERT INTO meta VALUES(?,?)", ("checkpoint_json", json.dumps(checkpoint)))
    connection.commit()
    connection.close()
    return first_hash, state_root


def _compact(tmp_path: Path):
    source = tmp_path / "source.sqlite3"
    first_hash, state_root = _database(source)
    archive = tmp_path / "full-history.glyphchain-snapshot"
    archive.write_bytes(b"retained-finality-anchored-archive")
    output = tmp_path / "compacted.sqlite3"
    manifest = {
        "snapshot_id": "ab" * 32,
        "ledger": {"height": 3, "database_sha256": _hash_file(source)},
    }
    result = compact_ledger_copy(
        database_path=source,
        output_path=output,
        archive_path=archive,
        snapshot_manifest=manifest,
        base_state=_state(),
        base_state_root=state_root,
        operator_id="owner-1",
        reason="bounded storage maintenance",
    )
    return source, output, archive, first_hash, result


def test_pruning_retains_tip_and_full_archive(tmp_path):
    _source, output, archive, _first_hash, result = _compact(tmp_path)
    connection = sqlite3.connect(output)
    assert connection.execute("SELECT height FROM blocks ORDER BY height").fetchall() == [(3,)]
    assert connection.execute("SELECT block_height FROM txs").fetchall() == [(3,)]
    base = json.loads(connection.execute(
        "SELECT value FROM meta WHERE key='pruning_base_json'"
    ).fetchone()[0])
    connection.close()
    assert base["base_height"] == 3
    assert base["operator_id"] == "owner-1"
    assert base["reason"] == "bounded storage maintenance"
    assert base["archive"]["sha256"] == _hash_file(archive)
    assert result["blocks_removed"] == 2
    assert result["transactions_removed"] == 2
    assert archive.read_bytes() == b"retained-finality-anchored-archive"


def test_historical_portable_inclusion_remains_verifiable_after_pruning(tmp_path):
    _source, output, _archive, first_hash, _result = _compact(tmp_path)
    connection = sqlite3.connect(output)
    assert connection.execute("SELECT 1 FROM txs WHERE tx_hash=?", (first_hash,)).fetchone() is None
    connection.close()
    root = merkle_root([hash_leaf(bytes.fromhex(first_hash))])
    assert verify_proof(hash_leaf(bytes.fromhex(first_hash)), [], root) is True


def test_pruning_rejects_changed_live_database_and_bad_state(tmp_path):
    source = tmp_path / "source.sqlite3"
    _first_hash, state_root = _database(source)
    archive = tmp_path / "archive"
    archive.write_bytes(b"archive")
    manifest = {"snapshot_id": "ab" * 32, "ledger": {"height": 3, "database_sha256": "00" * 32}}
    with pytest.raises(LedgerPruningError, match="live_database_changed"):
        compact_ledger_copy(
            database_path=source, output_path=tmp_path / "bad.sqlite3", archive_path=archive,
            snapshot_manifest=manifest, base_state=_state(), base_state_root=state_root,
        )
    manifest["ledger"]["database_sha256"] = _hash_file(source)
    with pytest.raises(LedgerPruningError, match="state_snapshot_root_mismatch"):
        compact_ledger_copy(
            database_path=source, output_path=tmp_path / "bad-state.sqlite3", archive_path=archive,
            snapshot_manifest=manifest, base_state=_state(), base_state_root="ff" * 32,
        )


def test_pruned_database_restarts_and_continues_at_next_height(tmp_path, monkeypatch):
    source, output, _archive, _first_hash, result = _compact(tmp_path)
    live = tmp_path / "live.sqlite3"
    shutil.copy2(source, live)
    monkeypatch.setenv("CHAIN_SIM_PERSIST", "1")
    monkeypatch.setenv("CHAIN_SIM_DB_PATH", str(live))
    monkeypatch.setenv("GLYPHCHAIN_LEDGER_MAX_BYTES", str(64 * 1024 * 1024))
    installed = install_verified_ledger_database(output, expected_sha256=result["database_sha256"])
    assert installed["installed"] is True
    assert get_block(1) is None
    assert get_block(3) is not None
    record = record_applied_tx(
        from_addr="new-origin", nonce=1, tx_type="DOCUMENT_PROOF_V1",
        payload={
            "schema_version": "glyphchain.document-proof.v1",
            "proof_id": "proof-4",
            "document_id_commitment": "11" * 32,
            "document_hash": "04" * 32,
            "signed_copy_hash": "22" * 32,
            "signatures_root": "33" * 32,
            "audit_root": "44" * 32,
            "issuer_key_id": "pruning-test-key",
            "completed_at_ms": 1_700_000_000_004,
            "policy_version": "pruning-test-v1",
            "verification_version": "sha256-merkle-ed25519-v1",
        },
        applied=True,
        result={},
    )
    assert record.block_height == 4
