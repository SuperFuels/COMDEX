"""Portable, finality-anchored GlyphChain ledger snapshots.

Snapshots are synchronization artifacts, not trust anchors.  A snapshot is
accepted only when its SQLite contents reconstruct the committed ledger block
and a v2 quorum certificate verifies against an independently pinned validator
checkpoint supplied by the receiving node.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import time
from typing import Any, Mapping
import zipfile

from backend.modules.consensus.finality_certificate import (
    CERTIFICATE_SCHEMA,
    verify_finality_certificate,
)
from backend.modules.consensus.finality_checkpoint import (
    FinalityCheckpointError,
    TrustedFinalityCheckpoint,
    normalize_checkpoint,
)
from backend.modules.consensus.ledger_commitment import normalize_ledger_block

from .ledger_storage import configured_ledger_limit_bytes


SNAPSHOT_SCHEMA = "glyphchain.ledger-snapshot.v1"
SNAPSHOT_MEDIA_TYPE = "application/vnd.tessaris.glyphchain-snapshot+zip"
SNAPSHOT_MEMBERS = frozenset({
    "manifest.json",
    "ledger.sqlite3",
    "finality-certificate.json",
    "validator-checkpoint.json",
})
MAX_METADATA_BYTES = 2 * 1024 * 1024


class LedgerSnapshotError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _hex64(value: Any, *, field: str) -> str:
    text = str(value or "").strip().lower()
    try:
        if len(text) != 64:
            raise ValueError
        bytes.fromhex(text)
    except ValueError as exc:
        raise LedgerSnapshotError(f"{field}_invalid") from exc
    return text


def _normalize_validator_checkpoint(value: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return normalize_checkpoint(value)
    except (FinalityCheckpointError, TypeError, ValueError, KeyError) as exc:
        raise LedgerSnapshotError("snapshot_validator_checkpoint_invalid") from exc


def _normalize_checkpoint_block(block: Mapping[str, Any], *, chain_id: str, height: int) -> dict[str, Any]:
    try:
        return normalize_ledger_block(block, chain_id=chain_id, height=height)
    except (TypeError, ValueError, KeyError) as exc:
        raise LedgerSnapshotError("snapshot_ledger_commitment_invalid") from exc


def _read_json_member(archive: zipfile.ZipFile, name: str) -> dict[str, Any]:
    info = archive.getinfo(name)
    if info.file_size > MAX_METADATA_BYTES:
        raise LedgerSnapshotError(f"snapshot_{name}_too_large")
    try:
        value = json.loads(archive.read(name).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError) as exc:
        raise LedgerSnapshotError(f"snapshot_{name}_invalid") from exc
    if not isinstance(value, dict):
        raise LedgerSnapshotError(f"snapshot_{name}_invalid")
    return value


def _validate_archive(archive: zipfile.ZipFile, *, max_database_bytes: int) -> None:
    names = [info.filename for info in archive.infolist()]
    if len(names) != len(set(names)) or set(names) != SNAPSHOT_MEMBERS:
        raise LedgerSnapshotError("snapshot_members_invalid")
    total = 0
    for info in archive.infolist():
        if info.is_dir() or info.filename.startswith(("/", "\\")) or ".." in Path(info.filename).parts:
            raise LedgerSnapshotError("snapshot_member_path_invalid")
        if info.flag_bits & 0x1:
            raise LedgerSnapshotError("snapshot_encrypted_member_not_supported")
        limit = max_database_bytes if info.filename == "ledger.sqlite3" else MAX_METADATA_BYTES
        if info.file_size <= 0 or info.file_size > limit:
            raise LedgerSnapshotError("snapshot_member_size_invalid")
        total += info.file_size
    if total > max_database_bytes + (3 * MAX_METADATA_BYTES):
        raise LedgerSnapshotError("snapshot_uncompressed_size_exceeded")


def _connect_read_only(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _validate_schema(connection: sqlite3.Connection) -> None:
    required = {
        "meta": {"key", "value"},
        "blocks": {"height", "created_at_ms", "header_json", "state_root", "txs_root"},
        "txs": {
            "tx_id", "tx_hash", "block_height", "tx_index", "from_addr", "nonce",
            "tx_type", "payload_json", "applied", "result_json", "fee_json",
        },
    }
    schema_rows = connection.execute(
        "SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
    ).fetchall()
    tables = {str(row[1]) for row in schema_rows if str(row[0]) == "table"}
    if tables != set(required):
        raise LedgerSnapshotError("snapshot_database_schema_invalid")
    if any(str(row[0]) in {"trigger", "view"} for row in schema_rows):
        raise LedgerSnapshotError("snapshot_database_active_schema_object_rejected")
    allowed_indexes = {"idx_txs_block", "idx_txs_from", "idx_txs_hash"}
    indexes = {str(row[1]) for row in schema_rows if str(row[0]) == "index"}
    if not indexes.issubset(allowed_indexes):
        raise LedgerSnapshotError("snapshot_database_schema_invalid")
    for table, wanted in required.items():
        columns = {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}
        if columns != wanted:
            raise LedgerSnapshotError("snapshot_database_schema_invalid")
    quick = connection.execute("PRAGMA quick_check").fetchone()
    if not quick or str(quick[0]).lower() != "ok":
        raise LedgerSnapshotError("snapshot_database_integrity_failed")
    foreign = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign:
        raise LedgerSnapshotError("snapshot_database_foreign_key_failed")


def _load_checkpoint(connection: sqlite3.Connection) -> dict[str, Any]:
    row = connection.execute("SELECT value FROM meta WHERE key=?", ("checkpoint_json",)).fetchone()
    if not row:
        raise LedgerSnapshotError("snapshot_ledger_checkpoint_missing")
    try:
        checkpoint = json.loads(str(row[0]))
    except json.JSONDecodeError as exc:
        raise LedgerSnapshotError("snapshot_ledger_checkpoint_invalid") from exc
    if not isinstance(checkpoint, dict):
        raise LedgerSnapshotError("snapshot_ledger_checkpoint_invalid")
    return checkpoint


def _checkpoint_block(connection: sqlite3.Connection, checkpoint: Mapping[str, Any]) -> dict[str, Any]:
    try:
        height = int(checkpoint.get("last_height") or 0)
    except (TypeError, ValueError) as exc:
        raise LedgerSnapshotError("snapshot_ledger_checkpoint_invalid") from exc
    if height <= 0:
        raise LedgerSnapshotError("snapshot_ledger_checkpoint_invalid")
    row = connection.execute(
        "SELECT created_at_ms, header_json, state_root, txs_root FROM blocks WHERE height=?",
        (height,),
    ).fetchone()
    if not row:
        raise LedgerSnapshotError("snapshot_checkpoint_block_missing")
    try:
        header = json.loads(str(row[1] or "{}"))
    except json.JSONDecodeError as exc:
        raise LedgerSnapshotError("snapshot_block_header_invalid") from exc
    if not isinstance(header, dict):
        raise LedgerSnapshotError("snapshot_block_header_invalid")
    state_root = _hex64(row[2] or checkpoint.get("last_state_root"), field="snapshot_state_root")
    txs_root = _hex64(row[3] or checkpoint.get("last_txs_root"), field="snapshot_txs_root")
    if not hmac.compare_digest(state_root, _hex64(checkpoint.get("last_state_root"), field="snapshot_checkpoint_state_root")):
        raise LedgerSnapshotError("snapshot_checkpoint_state_root_mismatch")
    if not hmac.compare_digest(txs_root, _hex64(checkpoint.get("last_txs_root"), field="snapshot_checkpoint_txs_root")):
        raise LedgerSnapshotError("snapshot_checkpoint_txs_root_mismatch")

    rows = connection.execute(
        """
        SELECT tx_id, tx_hash, tx_index, from_addr, nonce, tx_type, payload_json, applied
        FROM txs WHERE block_height=? ORDER BY tx_index ASC, tx_id ASC
        """,
        (height,),
    ).fetchall()
    txs: list[dict[str, Any]] = []
    for row_tx in rows:
        if int(row_tx[7] or 0) != 1:
            raise LedgerSnapshotError("snapshot_unapplied_checkpoint_transaction")
        try:
            payload = json.loads(str(row_tx[6] or "{}"))
        except json.JSONDecodeError as exc:
            raise LedgerSnapshotError("snapshot_transaction_payload_invalid") from exc
        if not isinstance(payload, dict):
            raise LedgerSnapshotError("snapshot_transaction_payload_invalid")
        txs.append({
            "tx_id": str(row_tx[0]),
            "tx_hash": str(row_tx[1]),
            "tx_index": int(row_tx[2]),
            "from_addr": str(row_tx[3]),
            "nonce": int(row_tx[4]),
            "tx_type": str(row_tx[5]),
            "payload": payload,
        })
    return {
        "height": height,
        "created_at_ms": int(row[0]),
        "header": {**header, "state_root": state_root, "txs_root": txs_root},
        "state_root": state_root,
        "txs_root": txs_root,
        "txs": txs,
    }


def _snapshot_manifest(
    *,
    database_path: Path,
    chain_id: str,
    network_id: str,
    block: Mapping[str, Any],
    commitment: Mapping[str, Any],
    certificate: Mapping[str, Any],
    checkpoint: Mapping[str, Any],
) -> dict[str, Any]:
    certificate_hash = sha256(_canonical(certificate)).hexdigest()
    checkpoint_hash = sha256(_canonical(checkpoint)).hexdigest()
    manifest: dict[str, Any] = {
        "schema_version": SNAPSHOT_SCHEMA,
        "created_at_ms": int(time.time() * 1000),
        "chain_id": str(chain_id),
        "network_id": str(network_id),
        "ledger": {
            "height": int(block["height"]),
            "state_root": str(block["state_root"]),
            "txs_root": str(commitment["txs_root"]),
            "ledger_commitment": str(commitment["ledger_commitment"]),
            "block_id": str(certificate.get("block_id") or ""),
            "database_sha256": _sha256_file(database_path),
            "database_bytes": int(database_path.stat().st_size),
        },
        "finality": {
            "certificate_sha256": certificate_hash,
            "validator_checkpoint_sha256": checkpoint_hash,
            "validator_checkpoint_id": str(checkpoint.get("checkpoint_id") or ""),
            "validator_set_root": str(checkpoint.get("validator_set_root") or ""),
        },
        "privacy": "ledger_state_and_public_finality_evidence_only_no_legal_documents_or_signer_identity",
    }
    manifest["snapshot_id"] = sha256(_canonical(manifest)).hexdigest()
    return manifest


@dataclass(frozen=True)
class VerifiedLedgerSnapshot:
    manifest: dict[str, Any]
    finality_certificate: dict[str, Any]
    database_path: Path
    extraction_root: Path

    def summary(self) -> dict[str, Any]:
        return {
            "schema_version": self.manifest["schema_version"],
            "snapshot_id": self.manifest["snapshot_id"],
            "chain_id": self.manifest["chain_id"],
            "network_id": self.manifest["network_id"],
            "ledger": dict(self.manifest["ledger"]),
            "finality": dict(self.manifest["finality"]),
            "verified": True,
        }

    def cleanup(self) -> None:
        shutil.rmtree(self.extraction_root, ignore_errors=True)


def export_ledger_snapshot(
    *,
    database_path: str | Path,
    output_path: str | Path,
    chain_id: str,
    network_id: str,
    finality_certificate: Mapping[str, Any],
    validator_checkpoint: Mapping[str, Any],
) -> dict[str, Any]:
    source = Path(database_path).expanduser().resolve()
    output = Path(output_path).expanduser().resolve()
    if not source.is_file():
        raise LedgerSnapshotError("snapshot_source_database_missing")
    checkpoint = _normalize_validator_checkpoint(validator_checkpoint)
    if checkpoint["chain_id"] != str(chain_id) or checkpoint["network_id"] != str(network_id):
        raise LedgerSnapshotError("snapshot_validator_checkpoint_network_mismatch")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="glyphchain-snapshot-export-") as temporary:
        backup_path = Path(temporary) / "ledger.sqlite3"
        source_connection = sqlite3.connect(str(source))
        destination = sqlite3.connect(str(backup_path))
        try:
            source_connection.backup(destination)
        finally:
            destination.close()
            source_connection.close()
        connection = _connect_read_only(backup_path)
        try:
            _validate_schema(connection)
            ledger_checkpoint = _load_checkpoint(connection)
            block = _checkpoint_block(connection, ledger_checkpoint)
        finally:
            connection.close()
        commitment = _normalize_checkpoint_block(block, chain_id=str(chain_id), height=int(block["height"]))
        certificate = dict(finality_certificate)
        if certificate.get("schema_version") != CERTIFICATE_SCHEMA:
            raise LedgerSnapshotError("snapshot_requires_v2_finality_certificate")
        verification = verify_finality_certificate(
            certificate,
            trusted_validator_set_root=checkpoint["validator_set_root"],
            expected_chain_id=str(chain_id),
            expected_height=int(block["height"]),
            expected_block_id=str(certificate.get("block_id") or ""),
            expected_ledger_commitment=str(commitment["ledger_commitment"]),
            expected_txs_root=str(commitment["txs_root"]),
        )
        if not verification.get("valid") or verification.get("trust_anchor_verified") is not True:
            raise LedgerSnapshotError("snapshot_finality_certificate_invalid")
        if str(certificate.get("network_id") or "") != str(network_id):
            raise LedgerSnapshotError("snapshot_finality_network_mismatch")
        if str(certificate.get("validator_set_checkpoint_id") or "") != checkpoint["checkpoint_id"]:
            raise LedgerSnapshotError("snapshot_finality_checkpoint_mismatch")
        manifest = _snapshot_manifest(
            database_path=backup_path,
            chain_id=str(chain_id),
            network_id=str(network_id),
            block=block,
            commitment=commitment,
            certificate=certificate,
            checkpoint=checkpoint,
        )
        temporary_output = output.with_suffix(output.suffix + ".tmp")
        try:
            with zipfile.ZipFile(temporary_output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                archive.write(backup_path, "ledger.sqlite3")
                archive.writestr("manifest.json", json.dumps(manifest, sort_keys=True, indent=2) + "\n")
                archive.writestr("finality-certificate.json", json.dumps(certificate, sort_keys=True, indent=2) + "\n")
                archive.writestr("validator-checkpoint.json", json.dumps(checkpoint, sort_keys=True, indent=2) + "\n")
            os.chmod(temporary_output, 0o600)
            os.replace(temporary_output, output)
        finally:
            temporary_output.unlink(missing_ok=True)
    return manifest


def export_current_finalized_snapshot(output_path: str | Path) -> dict[str, Any]:
    """Export the persisted checkpoint only when live consensus retained its QC."""
    from backend.modules.chain_sim.chain_sim_ledger import persist_database_path, persist_get_checkpoint
    from backend.modules.consensus.engine import get_engine
    from backend.modules.consensus.finality_checkpoint import load_trusted_checkpoint_from_env

    database = persist_database_path()
    ledger_checkpoint = persist_get_checkpoint() or {}
    height = int(ledger_checkpoint.get("last_height") or 0)
    if database is None or height <= 0:
        raise LedgerSnapshotError("snapshot_checkpoint_unavailable")
    trusted = load_trusted_checkpoint_from_env()
    if trusted is None:
        raise LedgerSnapshotError("snapshot_trusted_checkpoint_required")
    engine = get_engine()
    receipt = engine.finality_receipt(height=height)
    certificate = receipt.get("quorum_finality_certificate") if isinstance(receipt, dict) else None
    if not isinstance(certificate, dict):
        raise LedgerSnapshotError("snapshot_finality_certificate_unavailable")
    return export_ledger_snapshot(
        database_path=database,
        output_path=output_path,
        chain_id=engine.chain_id,
        network_id=engine.network_id,
        finality_certificate=certificate,
        validator_checkpoint=trusted.value,
    )


def verify_ledger_snapshot(
    snapshot_path: str | Path,
    *,
    trusted_checkpoint: TrustedFinalityCheckpoint,
    expected_chain_id: str,
    expected_network_id: str,
    minimum_height: int = 0,
    max_database_bytes: int | None = None,
) -> VerifiedLedgerSnapshot:
    source = Path(snapshot_path).expanduser().resolve()
    if not source.is_file():
        raise LedgerSnapshotError("snapshot_file_missing")
    database_limit = int(max_database_bytes or configured_ledger_limit_bytes())
    if source.stat().st_size > database_limit + (3 * MAX_METADATA_BYTES):
        raise LedgerSnapshotError("snapshot_archive_size_exceeded")
    extraction_root = Path(tempfile.mkdtemp(prefix="glyphchain-snapshot-verify-"))
    try:
        with zipfile.ZipFile(source, "r") as archive:
            _validate_archive(archive, max_database_bytes=database_limit)
            manifest = _read_json_member(archive, "manifest.json")
            certificate = _read_json_member(archive, "finality-certificate.json")
            bundled_checkpoint = _read_json_member(archive, "validator-checkpoint.json")
            database_path = extraction_root / "ledger.sqlite3"
            with archive.open("ledger.sqlite3", "r") as source_db, database_path.open("xb") as target_db:
                shutil.copyfileobj(source_db, target_db, length=1024 * 1024)
        if manifest.get("schema_version") != SNAPSHOT_SCHEMA:
            raise LedgerSnapshotError("snapshot_schema_unsupported")
        supplied_snapshot_id = _hex64(manifest.get("snapshot_id"), field="snapshot_id")
        unsigned_manifest = dict(manifest)
        unsigned_manifest.pop("snapshot_id", None)
        if not hmac.compare_digest(supplied_snapshot_id, sha256(_canonical(unsigned_manifest)).hexdigest()):
            raise LedgerSnapshotError("snapshot_manifest_digest_invalid")
        if manifest.get("chain_id") != expected_chain_id or manifest.get("network_id") != expected_network_id:
            raise LedgerSnapshotError("snapshot_network_identity_mismatch")
        normalized_bundled = _normalize_validator_checkpoint(bundled_checkpoint)
        if normalized_bundled["checkpoint_id"] != trusted_checkpoint.checkpoint_id:
            raise LedgerSnapshotError("snapshot_checkpoint_not_independently_trusted")
        if normalized_bundled["validator_set_root"] != trusted_checkpoint.validator_set_root:
            raise LedgerSnapshotError("snapshot_validator_set_not_independently_trusted")
        finality_manifest = dict(manifest.get("finality") or {})
        if finality_manifest.get("validator_checkpoint_id") != trusted_checkpoint.checkpoint_id:
            raise LedgerSnapshotError("snapshot_manifest_checkpoint_mismatch")
        if finality_manifest.get("validator_set_root") != trusted_checkpoint.validator_set_root:
            raise LedgerSnapshotError("snapshot_manifest_validator_set_mismatch")
        if sha256(_canonical(certificate)).hexdigest() != str(manifest.get("finality", {}).get("certificate_sha256") or ""):
            raise LedgerSnapshotError("snapshot_certificate_digest_mismatch")
        if sha256(_canonical(normalized_bundled)).hexdigest() != str(manifest.get("finality", {}).get("validator_checkpoint_sha256") or ""):
            raise LedgerSnapshotError("snapshot_checkpoint_digest_mismatch")
        if _sha256_file(database_path) != str(manifest.get("ledger", {}).get("database_sha256") or ""):
            raise LedgerSnapshotError("snapshot_database_digest_mismatch")
        if database_path.stat().st_size != int(manifest.get("ledger", {}).get("database_bytes") or -1):
            raise LedgerSnapshotError("snapshot_database_size_mismatch")
        connection = _connect_read_only(database_path)
        try:
            _validate_schema(connection)
            ledger_checkpoint = _load_checkpoint(connection)
            block = _checkpoint_block(connection, ledger_checkpoint)
        finally:
            connection.close()
        if int(block["height"]) < max(0, int(minimum_height)):
            raise LedgerSnapshotError("snapshot_rollback_rejected")
        commitment = _normalize_checkpoint_block(block, chain_id=expected_chain_id, height=int(block["height"]))
        ledger_manifest = dict(manifest.get("ledger") or {})
        expected_values = {
            "height": int(block["height"]),
            "state_root": str(block["state_root"]),
            "txs_root": str(commitment["txs_root"]),
            "ledger_commitment": str(commitment["ledger_commitment"]),
            "block_id": str(certificate.get("block_id") or ""),
        }
        if any(str(ledger_manifest.get(key)) != str(value) for key, value in expected_values.items()):
            raise LedgerSnapshotError("snapshot_manifest_ledger_mismatch")
        if certificate.get("schema_version") != CERTIFICATE_SCHEMA:
            raise LedgerSnapshotError("snapshot_requires_v2_finality_certificate")
        if str(certificate.get("network_id") or "") != expected_network_id:
            raise LedgerSnapshotError("snapshot_finality_network_mismatch")
        if str(certificate.get("validator_set_checkpoint_id") or "") != trusted_checkpoint.checkpoint_id:
            raise LedgerSnapshotError("snapshot_finality_checkpoint_mismatch")
        verification = verify_finality_certificate(
            certificate,
            trusted_validator_set_root=trusted_checkpoint.validator_set_root,
            expected_chain_id=expected_chain_id,
            expected_height=int(block["height"]),
            expected_block_id=str(expected_values["block_id"]),
            expected_ledger_commitment=str(commitment["ledger_commitment"]),
            expected_txs_root=str(commitment["txs_root"]),
        )
        if not verification.get("valid") or verification.get("trust_anchor_verified") is not True:
            raise LedgerSnapshotError("snapshot_finality_certificate_invalid")
        return VerifiedLedgerSnapshot(
            manifest=dict(manifest),
            finality_certificate=dict(certificate),
            database_path=database_path,
            extraction_root=extraction_root,
        )
    except (LedgerSnapshotError, zipfile.BadZipFile, KeyError, OSError, sqlite3.DatabaseError, TypeError, ValueError) as exc:
        shutil.rmtree(extraction_root, ignore_errors=True)
        if isinstance(exc, LedgerSnapshotError):
            raise
        raise LedgerSnapshotError("snapshot_verification_failed") from exc
