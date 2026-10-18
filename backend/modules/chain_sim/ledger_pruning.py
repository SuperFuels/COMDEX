"""Proof-preserving, operator-gated GlyphChain ledger compaction.

Pruning is never automatic.  Before historical rows are removed, the exact
live database must already be present in a finality-anchored snapshot archive.
The hot database retains the finalized tip block and its transaction envelopes,
plus a canonical state base used for deterministic restart.  Historical Legal
proofs remain independently verifiable from their portable receipts and from
the retained full snapshot archive.
"""

from __future__ import annotations

from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import sqlite3
import time
from typing import Any, Mapping

from backend.modules.chain_sim.canonical_codec import canonical_hash_hex


PRUNING_BASE_SCHEMA = "glyphchain.pruning-base.v1"


class LedgerPruningError(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _checkpoint(connection: sqlite3.Connection) -> dict[str, Any]:
    row = connection.execute("SELECT value FROM meta WHERE key='checkpoint_json'").fetchone()
    if not row:
        raise LedgerPruningError("ledger_pruning_checkpoint_missing")
    try:
        value = json.loads(str(row[0]))
    except json.JSONDecodeError as exc:
        raise LedgerPruningError("ledger_pruning_checkpoint_invalid") from exc
    if not isinstance(value, dict) or int(value.get("last_height") or 0) <= 0:
        raise LedgerPruningError("ledger_pruning_checkpoint_invalid")
    return value


def compact_ledger_copy(
    *,
    database_path: str | Path,
    output_path: str | Path,
    archive_path: str | Path,
    snapshot_manifest: Mapping[str, Any],
    base_state: Mapping[str, Any],
    base_state_root: str,
    operator_id: str = "local-operator",
    reason: str = "operator-approved storage maintenance",
) -> dict[str, Any]:
    """Create a compacted copy after binding it to a retained full snapshot."""
    source = Path(database_path).expanduser().resolve()
    target = Path(output_path).expanduser().resolve()
    archive = Path(archive_path).expanduser().resolve()
    if not source.is_file():
        raise LedgerPruningError("ledger_pruning_database_missing")
    if not archive.is_file():
        raise LedgerPruningError("ledger_pruning_verified_archive_missing")
    if source == target:
        raise LedgerPruningError("ledger_pruning_output_must_be_separate")
    ledger_manifest = dict(snapshot_manifest.get("ledger") or {})
    expected_database_hash = str(ledger_manifest.get("database_sha256") or "").lower()
    if not expected_database_hash or not hmac.compare_digest(_file_hash(source), expected_database_hash):
        raise LedgerPruningError("ledger_pruning_live_database_changed_since_archive")
    state = dict(base_state)
    computed_state_root = canonical_hash_hex(state)
    if not hmac.compare_digest(computed_state_root, str(base_state_root or "").lower()):
        raise LedgerPruningError("ledger_pruning_state_snapshot_root_mismatch")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    source_connection = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    target_connection = sqlite3.connect(target)
    try:
        source_connection.backup(target_connection)
    finally:
        source_connection.close()
        target_connection.close()
    os.chmod(target, 0o600)

    connection = sqlite3.connect(target)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        checkpoint = _checkpoint(connection)
        base_height = int(checkpoint["last_height"])
        if int(ledger_manifest.get("height") or 0) != base_height:
            raise LedgerPruningError("ledger_pruning_archive_height_mismatch")
        if not hmac.compare_digest(str(checkpoint.get("last_state_root") or ""), computed_state_root):
            raise LedgerPruningError("ledger_pruning_checkpoint_state_root_mismatch")
        if connection.execute("SELECT 1 FROM blocks WHERE height=?", (base_height,)).fetchone() is None:
            raise LedgerPruningError("ledger_pruning_anchor_block_missing")
        before_blocks = int(connection.execute("SELECT COUNT(*) FROM blocks").fetchone()[0])
        before_transactions = int(connection.execute("SELECT COUNT(*) FROM txs").fetchone()[0])
        archive_hash = _file_hash(archive)
        pruning_base = {
            "schema_version": PRUNING_BASE_SCHEMA,
            "base_height": base_height,
            "state": state,
            "state_root": computed_state_root,
            "created_at_ms": int(time.time() * 1000),
            "operator_id": str(operator_id or "")[:240],
            "reason": str(reason or "")[:1000],
            "archive": {
                "snapshot_id": str(snapshot_manifest.get("snapshot_id") or ""),
                "sha256": archive_hash,
                "byte_length": archive.stat().st_size,
            },
            "proof_verification": "portable_receipts_and_retained_finality_anchored_snapshot",
        }
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DELETE FROM blocks WHERE height < ?", (base_height,))
        connection.execute(
            "INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)",
            ("pruning_base_json", _canonical(pruning_base)),
        )
        connection.commit()
        quick = connection.execute("PRAGMA quick_check").fetchone()
        foreign = connection.execute("PRAGMA foreign_key_check").fetchall()
        if not quick or str(quick[0]).lower() != "ok" or foreign:
            raise LedgerPruningError("ledger_pruning_compacted_database_invalid")
        after_blocks = int(connection.execute("SELECT COUNT(*) FROM blocks").fetchone()[0])
        after_transactions = int(connection.execute("SELECT COUNT(*) FROM txs").fetchone()[0])
        connection.execute("VACUUM")
    except Exception:
        connection.rollback()
        connection.close()
        target.unlink(missing_ok=True)
        raise
    else:
        connection.close()
    return {
        "schema_version": PRUNING_BASE_SCHEMA,
        "base_height": base_height,
        "archive_snapshot_id": pruning_base["archive"]["snapshot_id"],
        "archive_sha256": pruning_base["archive"]["sha256"],
        "blocks_removed": before_blocks - after_blocks,
        "transactions_removed": before_transactions - after_transactions,
        "blocks_retained": after_blocks,
        "transactions_retained": after_transactions,
        "database_sha256": _file_hash(target),
        "restart_required": True,
        "automatic": False,
    }
