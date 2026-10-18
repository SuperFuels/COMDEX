from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.modules.aion_business.runtime.business_vault import BusinessVaultLayout


SNAPSHOT_SCHEMA = "tessaris.business-vault-snapshot.v1"
CHUNK_BYTES = 4 * 1024 * 1024


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _within(candidate: Path, parent: Path) -> bool:
    try:
        candidate.resolve(strict=False).relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


class VaultSnapshotError(ValueError):
    pass


class VaultSnapshotService:
    """Chunked encrypted external snapshot and fail-closed restore boundary."""

    def __init__(self, layout: BusinessVaultLayout, *, encryption_key: bytes) -> None:
        if len(encryption_key) != 32:
            raise VaultSnapshotError("snapshot_encryption_key_invalid")
        self.layout = layout
        self.cipher = AESGCM(bytes(encryption_key))

    def _aad(self, snapshot_id: str, relative_path: str, chunk: int) -> bytes:
        return _canonical(
            {
                "schema_version": SNAPSHOT_SCHEMA,
                "snapshot_id": snapshot_id,
                "relative_path": relative_path,
                "chunk": chunk,
            }
        )

    def _database_backup(self, target: Path) -> None:
        source_path = self.layout.records / "guardian.sqlite3"
        if not source_path.exists():
            raise VaultSnapshotError("snapshot_guardian_database_missing")
        with sqlite3.connect(source_path) as source, sqlite3.connect(target) as destination:
            source.backup(destination)
            destination.execute("PRAGMA integrity_check")

    def create_snapshot(
        self,
        *,
        destination_root: str | Path,
        snapshot_id: str,
        created_at: str,
    ) -> Path:
        snapshot_id = str(snapshot_id or "").strip()
        if not snapshot_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for char in snapshot_id):
            raise VaultSnapshotError("snapshot_id_invalid")
        destination_root = Path(destination_root).expanduser().resolve(strict=False)
        if _within(destination_root, self.layout.root) or _within(self.layout.root, destination_root):
            raise VaultSnapshotError("snapshot_destination_vault_overlap")
        destination_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        final = destination_root / f"{snapshot_id}.tessaris-snapshot"
        if final.exists():
            raise VaultSnapshotError("snapshot_already_exists")
        staging = destination_root / f".{snapshot_id}.{uuid4().hex}.staging"
        staging.mkdir(mode=0o700)
        try:
            database_copy = staging / ".guardian.sqlite3.consistent"
            self._database_backup(database_copy)
            sources: list[tuple[str, Path]] = [
                ("vault.manifest.json", self.layout.manifest),
                ("records/guardian.sqlite3", database_copy),
            ]
            for path in sorted(self.layout.files.rglob("*")):
                if path.is_file():
                    sources.append((path.relative_to(self.layout.root).as_posix(), path))

            chunks_dir = staging / "chunks"
            chunks_dir.mkdir(mode=0o700)
            entries: list[dict[str, Any]] = []
            chunk_number = 0
            for relative_path, source in sources:
                digest = hashlib.sha256()
                byte_length = 0
                chunk_names: list[str] = []
                with source.open("rb") as handle:
                    while True:
                        raw = handle.read(CHUNK_BYTES)
                        if not raw:
                            break
                        digest.update(raw)
                        byte_length += len(raw)
                        nonce = os.urandom(12)
                        sealed = nonce + self.cipher.encrypt(
                            nonce, raw, self._aad(snapshot_id, relative_path, len(chunk_names))
                        )
                        name = f"{chunk_number:012d}.chunk"
                        (chunks_dir / name).write_bytes(sealed)
                        os.chmod(chunks_dir / name, 0o600)
                        chunk_names.append(name)
                        chunk_number += 1
                entries.append(
                    {
                        "relative_path": relative_path,
                        "byte_length": byte_length,
                        "plaintext_sha256": digest.hexdigest(),
                        "chunks": chunk_names,
                    }
                )

            index = {
                "schema_version": SNAPSHOT_SCHEMA,
                "snapshot_id": snapshot_id,
                "created_at": created_at,
                "entries": entries,
            }
            index_raw = _canonical(index)
            index_nonce = os.urandom(12)
            index_aad = _canonical({"schema_version": SNAPSHOT_SCHEMA, "snapshot_id": snapshot_id, "part": "index"})
            (staging / "index.enc").write_bytes(
                index_nonce + self.cipher.encrypt(index_nonce, index_raw, index_aad)
            )
            os.chmod(staging / "index.enc", 0o600)
            header = {
                "schema_version": SNAPSHOT_SCHEMA,
                "snapshot_id": snapshot_id,
                "encryption": "AES-256-GCM-chunked",
                "index_sha256": _sha256((staging / "index.enc").read_bytes()),
                "key_material_in_snapshot": False,
            }
            (staging / "snapshot.json").write_text(
                json.dumps(header, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            os.chmod(staging / "snapshot.json", 0o600)
            database_copy.unlink(missing_ok=True)
            os.replace(staging, final)
            return final
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise

    def inspect_snapshot(self, *, snapshot_path: str | Path) -> dict[str, Any]:
        """Authenticate and return the content-free encrypted index metadata."""

        snapshot = Path(snapshot_path).expanduser().resolve(strict=True)
        header = json.loads((snapshot / "snapshot.json").read_text(encoding="utf-8"))
        if header.get("schema_version") != SNAPSHOT_SCHEMA:
            raise VaultSnapshotError("snapshot_schema_invalid")
        snapshot_id = str(header.get("snapshot_id") or "")
        index_sealed = (snapshot / "index.enc").read_bytes()
        if _sha256(index_sealed) != header.get("index_sha256") or len(index_sealed) < 29:
            raise VaultSnapshotError("snapshot_index_integrity_failed")
        index_aad = _canonical(
            {"schema_version": SNAPSHOT_SCHEMA, "snapshot_id": snapshot_id, "part": "index"}
        )
        try:
            index = json.loads(
                self.cipher.decrypt(index_sealed[:12], index_sealed[12:], index_aad)
            )
        except Exception as exc:
            raise VaultSnapshotError("snapshot_index_decryption_failed") from exc
        if index.get("schema_version") != SNAPSHOT_SCHEMA or index.get("snapshot_id") != snapshot_id:
            raise VaultSnapshotError("snapshot_index_identity_invalid")
        return {
            "schema_version": SNAPSHOT_SCHEMA,
            "snapshot_id": snapshot_id,
            "created_at": index.get("created_at"),
            "index_sha256": str(header["index_sha256"]),
            "encryption": str(header.get("encryption") or ""),
            "key_material_in_snapshot": bool(header.get("key_material_in_snapshot")),
            "entries": [
                {
                    "relative_path": str(entry["relative_path"]),
                    "byte_length": int(entry["byte_length"]),
                    "plaintext_sha256": str(entry["plaintext_sha256"]),
                    "chunk_count": len(entry.get("chunks", [])),
                }
                for entry in index.get("entries", [])
            ],
        }

    def restore_snapshot(
        self,
        *,
        snapshot_path: str | Path,
        destination_root: str | Path,
    ) -> BusinessVaultLayout:
        snapshot = Path(snapshot_path).expanduser().resolve(strict=True)
        destination = Path(destination_root).expanduser().resolve(strict=False)
        if destination.exists() and any(destination.iterdir()):
            raise VaultSnapshotError("restore_destination_not_empty")
        header = json.loads((snapshot / "snapshot.json").read_text(encoding="utf-8"))
        inspected = self.inspect_snapshot(snapshot_path=snapshot)
        snapshot_id = inspected["snapshot_id"]
        index_sealed = (snapshot / "index.enc").read_bytes()
        index_aad = _canonical({"schema_version": SNAPSHOT_SCHEMA, "snapshot_id": snapshot_id, "part": "index"})
        index = json.loads(self.cipher.decrypt(index_sealed[:12], index_sealed[12:], index_aad))

        destination.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            for entry in index.get("entries", []):
                relative = Path(str(entry.get("relative_path") or ""))
                if relative.is_absolute() or not relative.parts or ".." in relative.parts:
                    raise VaultSnapshotError("snapshot_entry_path_invalid")
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                descriptor, temporary_name = tempfile.mkstemp(prefix=".restore-", dir=target.parent)
                digest = hashlib.sha256()
                byte_length = 0
                try:
                    with os.fdopen(descriptor, "wb") as handle:
                        for number, chunk_name in enumerate(entry.get("chunks", [])):
                            if Path(str(chunk_name)).name != chunk_name:
                                raise VaultSnapshotError("snapshot_chunk_name_invalid")
                            sealed = (snapshot / "chunks" / chunk_name).read_bytes()
                            raw = self.cipher.decrypt(
                                sealed[:12],
                                sealed[12:],
                                self._aad(snapshot_id, relative.as_posix(), number),
                            )
                            handle.write(raw)
                            digest.update(raw)
                            byte_length += len(raw)
                        handle.flush()
                        os.fsync(handle.fileno())
                    if byte_length != int(entry["byte_length"]) or digest.hexdigest() != entry["plaintext_sha256"]:
                        raise VaultSnapshotError("snapshot_entry_integrity_failed")
                    os.chmod(temporary_name, 0o600)
                    os.replace(temporary_name, target)
                finally:
                    Path(temporary_name).unlink(missing_ok=True)
            return BusinessVaultLayout.for_root(destination)
        except Exception:
            shutil.rmtree(destination, ignore_errors=True)
            raise
