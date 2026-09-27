from __future__ import annotations

import sqlite3

import pytest

from backend.modules.chain_sim import chain_sim_ledger as ledger
from backend.modules.chain_sim.ledger_storage import (
    LedgerStorageLimitError,
    assert_ledger_write_capacity,
    configure_sqlite_storage_bounds,
    ledger_storage_status,
)


def test_status_counts_database_wal_and_shared_memory_without_exposing_paths(tmp_path):
    database = tmp_path / "ledger.sqlite3"
    database.write_bytes(b"d" * 100)
    (tmp_path / "ledger.sqlite3-wal").write_bytes(b"w" * 200)
    (tmp_path / "ledger.sqlite3-shm").write_bytes(b"s" * 300)
    status = ledger_storage_status(database, max_bytes=1000)
    assert status["used_bytes"] == 600
    assert status["remaining_bytes"] == 400
    assert status["utilization_percent"] == 60.0
    assert str(database) not in str(status)


def test_capacity_gate_reserves_headroom_and_fails_closed(tmp_path, monkeypatch):
    database = tmp_path / "ledger.sqlite3"
    database.write_bytes(b"x" * 700)
    monkeypatch.setenv("GLYPHCHAIN_LEDGER_RESERVE_BYTES", "200")
    assert_ledger_write_capacity(database, estimated_growth_bytes=99, max_bytes=1000)
    with pytest.raises(LedgerStorageLimitError, match="capacity_reached"):
        assert_ledger_write_capacity(database, estimated_growth_bytes=101, max_bytes=1000)


def test_sqlite_main_database_receives_hard_page_bound(tmp_path, monkeypatch):
    database = tmp_path / "ledger.sqlite3"
    monkeypatch.setenv("GLYPHCHAIN_LEDGER_RESERVE_BYTES", str(1024 * 1024))
    connection = sqlite3.connect(database)
    try:
        status = configure_sqlite_storage_bounds(connection, database, max_bytes=8 * 1024 * 1024)
        assert status["database_page_limit"] > 0
        assert status["wal_autocheckpoint_pages"] == 64
        assert connection.execute("PRAGMA max_page_count").fetchone()[0] == status["database_page_limit"]
    finally:
        connection.close()


def test_new_transaction_is_not_accepted_when_persistent_capacity_is_exhausted(tmp_path, monkeypatch):
    database = tmp_path / "ledger.sqlite3"
    monkeypatch.setenv("CHAIN_SIM_DB_PATH", str(database))
    monkeypatch.setenv("CHAIN_SIM_PERSIST", "1")
    monkeypatch.setenv("GLYPHCHAIN_LEDGER_MAX_BYTES", str(8 * 1024 * 1024))
    monkeypatch.setenv("GLYPHCHAIN_LEDGER_RESERVE_BYTES", str((8 * 1024 * 1024) - 16 * 1024))
    ledger.reset_ledger(clear_persist=False)
    with pytest.raises(LedgerStorageLimitError, match="capacity_reached"):
        ledger.record_applied_tx(
            from_addr="acct-a", nonce=1, tx_type="DOCUMENT_PROOF_V1",
            payload={"proof_id": "proof-capacity"}, applied=True, result={"ok": True},
        )
    assert ledger.list_txs(limit=10) == []


def test_duplicate_transaction_remains_readable_when_new_writes_are_blocked(tmp_path, monkeypatch):
    database = tmp_path / "ledger.sqlite3"
    monkeypatch.setenv("CHAIN_SIM_DB_PATH", str(database))
    monkeypatch.setenv("CHAIN_SIM_PERSIST", "1")
    monkeypatch.setenv("GLYPHCHAIN_LEDGER_MAX_BYTES", str(8 * 1024 * 1024))
    monkeypatch.setenv("GLYPHCHAIN_LEDGER_RESERVE_BYTES", str(1024 * 1024))
    ledger.reset_ledger(clear_persist=False)
    first = ledger.record_applied_tx(
        from_addr="acct-a", nonce=7, tx_type="DOCUMENT_PROOF_V1",
        payload={"proof_id": "proof-existing"}, applied=True, result={"ok": True},
    )
    monkeypatch.setenv("GLYPHCHAIN_LEDGER_RESERVE_BYTES", str((8 * 1024 * 1024) - 16 * 1024))
    duplicate = ledger.record_applied_tx(
        from_addr="acct-a", nonce=7, tx_type="DOCUMENT_PROOF_V1",
        payload={"proof_id": "proof-existing"}, applied=True, result={"ok": True},
    )
    assert duplicate.tx_id == first.tx_id
