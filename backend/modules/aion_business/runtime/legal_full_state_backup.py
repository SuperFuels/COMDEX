"""Encrypted, bounded recovery packages for Legal and GlyphChain device state.

The package deliberately does not copy raw Keychain/development key files.  Legal
and GlyphChain private keys are exported through their existing password-wrapped
recovery formats, while the ledger is captured with SQLite's online-backup API.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path, PurePosixPath
import secrets
import shutil
import sqlite3
import struct
import tempfile
from typing import Any, Mapping
from uuid import uuid4
import zipfile

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from backend.modules.aion_business.runtime.legal_secure_storage import LegalKeyStore
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.p2p.network_identity import NetworkIdentityStore


class LegalFullStateBackupError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_component(value: str, label: str) -> str:
    clean = str(value or "").strip()
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    if not clean or clean in {".", ".."} or any(char not in allowed for char in clean):
        raise LegalFullStateBackupError(f"invalid_{label}")
    return clean


@dataclass(frozen=True)
class LegalFullStateLayout:
    legal_roots: Mapping[str, Path]
    glyphchain_state_root: Path
    ledger_database: Path | None
    network_identity_root: Path
    chain_id: str
    node_id: str
    checkpoint_path: Path | None = None
    independent_pin_path: Path | None = None
    checkpoint_inline: Mapping[str, Any] | None = None
    independent_pin: Mapping[str, str] | None = None

    @classmethod
    def from_environment(cls) -> "LegalFullStateLayout":
        state_root = Path(str(os.getenv("GLYPHCHAIN_STATE_DIR") or ".glyphchain_state")).expanduser()
        configured_identity = str(os.getenv("GLYPHCHAIN_NETWORK_KEY_DIR") or "").strip()
        configured_ledger = str(os.getenv("CHAIN_SIM_DB_PATH") or "").strip()
        checkpoint = str(os.getenv("GLYPHCHAIN_FINALITY_CHECKPOINT_PATH") or "").strip()
        checkpoint_inline = str(os.getenv("GLYPHCHAIN_FINALITY_CHECKPOINT_JSON") or "").strip()
        pin = str(os.getenv("GLYPHCHAIN_INDEPENDENT_PIN_PATH") or "").strip()
        checkpoint_id = str(os.getenv("GLYPHCHAIN_TRUSTED_CHECKPOINT_ID") or "").strip()
        validator_root = str(os.getenv("GLYPHCHAIN_TRUSTED_VALIDATOR_SET_ROOT") or "").strip()
        if configured_ledger:
            ledger = Path(configured_ledger).expanduser()
        else:
            ledger = Path(__file__).resolve().parents[4] / "data" / "chain_sim.sqlite3"
        return cls(
            legal_roots={
                "signing": AIONBusinessPaths.LEGAL_SIGNING,
                "matters": AIONBusinessPaths.LEGAL_MATTERS,
                "documents": AIONBusinessPaths.LEGAL_DOCUMENTS,
                "templates": AIONBusinessPaths.LEGAL_TEMPLATES,
            },
            glyphchain_state_root=state_root,
            ledger_database=ledger,
            network_identity_root=(Path(configured_identity).expanduser() if configured_identity else state_root / "network-identity"),
            chain_id=str(os.getenv("GLYPHCHAIN_CHAIN_ID") or os.getenv("CHAIN_ID") or "glyphchain-dev"),
            node_id=str(os.getenv("GLYPHCHAIN_NODE_ID") or os.getenv("P2P_NODE_ID") or "dev-node"),
            checkpoint_path=Path(checkpoint).expanduser() if checkpoint else None,
            independent_pin_path=Path(pin).expanduser() if pin else None,
            checkpoint_inline=(json.loads(checkpoint_inline) if checkpoint_inline else None),
            independent_pin={
                key: value for key, value in {
                    "checkpoint_id": checkpoint_id,
                    "validator_set_root": validator_root,
                }.items() if value
            } or None,
        )


class LegalFullStateBackupService:
    """Create and restore one authenticated device-recovery package."""

    SCHEMA_VERSION = "tessaris.legal-glyphchain-full-state.v1"
    ENVELOPE_VERSION = "tessaris.encrypted-full-state-backup.v1"
    MAGIC = b"TESSARIS-FULL-STATE-V1\n"
    CHUNK_BYTES = 4 * 1024 * 1024
    MAX_FILES = 50_000
    MAX_FILE_BYTES = 512 * 1024 * 1024
    MAX_ARCHIVE_BYTES = 4 * 1024 * 1024 * 1024
    LEGAL_PURPOSES = ("signing", "matters", "documents", "templates")

    def __init__(self, layout: LegalFullStateLayout | None = None) -> None:
        self.layout = layout or LegalFullStateLayout.from_environment()
        if set(self.layout.legal_roots) != set(self.LEGAL_PURPOSES):
            raise LegalFullStateBackupError("legal_backup_roots_incomplete")
        if self.layout.checkpoint_path and self.layout.checkpoint_inline:
            raise LegalFullStateBackupError("configure_checkpoint_path_or_inline_not_both")
        if self.layout.checkpoint_inline is not None and not isinstance(self.layout.checkpoint_inline, Mapping):
            raise LegalFullStateBackupError("inline_checkpoint_must_be_object")

    def create_backup(
        self,
        destination: str | Path,
        *,
        password: str,
        workspace_id: str,
        actor_id: str,
        confirmation: str,
    ) -> dict[str, Any]:
        if confirmation != "EXPORT COMPLETE LEGAL AND GLYPHCHAIN STATE":
            raise LegalFullStateBackupError("full_state_export_confirmation_required")
        self._validate_password(password)
        workspace = _safe_component(workspace_id, "workspace_id")
        actor = " ".join(str(actor_id or "").split()).strip()[:160]
        if not actor:
            raise LegalFullStateBackupError("full_state_export_actor_required")
        target = Path(destination).expanduser().resolve()
        if target.exists():
            raise LegalFullStateBackupError("backup_destination_already_exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        backup_id = f"full-state-{uuid4().hex}"
        self._append_recovery_event(
            "EXPORT_STARTED", backup_id=backup_id, actor_id=actor,
            details={"workspace_id": workspace},
        )
        with tempfile.TemporaryDirectory(prefix="tessaris-full-state-export-") as temporary:
            stage = Path(temporary)
            payload_root = stage / "payload"
            payload_root.mkdir()
            excluded = self._excluded_source_paths()
            for purpose in self.LEGAL_PURPOSES:
                self._copy_tree(
                    Path(self.layout.legal_roots[purpose]),
                    payload_root / "legal" / purpose,
                    excluded=excluded,
                )
            self._copy_tree(
                self.layout.glyphchain_state_root,
                payload_root / "glyphchain" / "state",
                excluded=excluded,
            )
            ledger_present = bool(self.layout.ledger_database and self.layout.ledger_database.is_file())
            if ledger_present:
                self._sqlite_backup(self.layout.ledger_database, payload_root / "glyphchain" / "ledger.sqlite3")
            self._copy_optional_file(self.layout.checkpoint_path, payload_root / "trust" / "validator-checkpoint.json")
            self._copy_optional_file(self.layout.independent_pin_path, payload_root / "trust" / "independent-pin.json")
            if not (payload_root / "trust" / "validator-checkpoint.json").exists() and self.layout.checkpoint_inline:
                self._write_json_file(payload_root / "trust" / "validator-checkpoint.json", self.layout.checkpoint_inline)
            if not (payload_root / "trust" / "independent-pin.json").exists() and self.layout.independent_pin:
                self._write_json_file(payload_root / "trust" / "independent-pin.json", self.layout.independent_pin)
            self._validate_copied_trust_material(payload_root / "trust")

            recovery = {
                "schema_version": "tessaris.full-state-key-recovery.v1",
                "legal": {
                    purpose: LegalKeyStore(self.layout.legal_roots[purpose]).export_recovery_bundle(password)
                    for purpose in self.LEGAL_PURPOSES
                },
                "network_identity": None,
            }
            identity_store = NetworkIdentityStore(
                self.layout.network_identity_root,
                chain_id=self.layout.chain_id,
                node_id=self.layout.node_id,
            )
            if identity_store.path.is_file():
                recovery["network_identity"] = identity_store.export_recovery_bundle(password)
            (payload_root / "recovery").mkdir(parents=True, exist_ok=True)
            (payload_root / "recovery" / "key-recovery.json").write_bytes(_canonical(recovery))

            files = self._manifest_files(payload_root)
            manifest = {
                "schema_version": self.SCHEMA_VERSION,
                "backup_id": backup_id,
                "created_at": _utc_now(),
                "workspace_id": workspace,
                "created_by": actor,
                "chain_id": self.layout.chain_id,
                "node_id": self.layout.node_id,
                "ledger_present": ledger_present,
                "checkpoint_present": (payload_root / "trust" / "validator-checkpoint.json").is_file(),
                "independent_pin_present": (payload_root / "trust" / "independent-pin.json").is_file(),
                "network_identity_recovery_present": recovery["network_identity"] is not None,
                "raw_private_keys_in_archive": False,
                "files": files,
                "files_sha256": sha256(_canonical(files)).hexdigest(),
            }
            (payload_root / "manifest.json").write_bytes(_canonical(manifest))
            archive = stage / "payload.zip"
            self._write_zip(payload_root, archive)
            archive_bytes = archive.stat().st_size
            if archive_bytes > self.MAX_ARCHIVE_BYTES:
                raise LegalFullStateBackupError("backup_archive_too_large")
            archive_hash = _sha256_file(archive)
            chunk_count = (archive_bytes + self.CHUNK_BYTES - 1) // self.CHUNK_BYTES
            header = {
                "schema_version": self.ENVELOPE_VERSION,
                "backup_id": backup_id,
                "created_at": manifest["created_at"],
                "kdf": "scrypt-n32768-r8-p1",
                "cipher": "AES-256-GCM-chunked",
                "chunk_bytes": self.CHUNK_BYTES,
                "chunk_count": chunk_count,
                "archive_bytes": archive_bytes,
                "archive_sha256": archive_hash,
                "salt_base64": base64.b64encode(secrets.token_bytes(16)).decode("ascii"),
                "nonce_prefix_base64": base64.b64encode(secrets.token_bytes(8)).decode("ascii"),
            }
            self._encrypt_archive(archive, target, password=password, header=header)
        os.chmod(target, 0o600)
        inspected = self.inspect_backup(target, password=password)
        self._append_recovery_event(
            "EXPORT_COMPLETED", backup_id=backup_id, actor_id=actor,
            details={"archive_sha256": inspected["archive_sha256"]},
        )
        return {**inspected, "path": str(target), "raw_private_keys_exposed": False}

    def inspect_backup(self, source: str | Path, *, password: str) -> dict[str, Any]:
        self._validate_password(password)
        source_path = Path(source).expanduser().resolve()
        with tempfile.TemporaryDirectory(prefix="tessaris-full-state-inspect-") as temporary:
            archive = Path(temporary) / "payload.zip"
            header = self._decrypt_archive(source_path, archive, password=password)
            manifest = self._validate_zip(archive)
            self._assert_header_manifest(header, manifest)
        return {
            "verified": True,
            "backup_id": manifest["backup_id"],
            "created_at": manifest["created_at"],
            "workspace_id": manifest["workspace_id"],
            "chain_id": manifest["chain_id"],
            "node_id": manifest["node_id"],
            "file_count": len(manifest["files"]),
            "archive_bytes": header["archive_bytes"],
            "archive_sha256": header["archive_sha256"],
            "ledger_present": bool(manifest["ledger_present"]),
            "checkpoint_present": bool(manifest["checkpoint_present"]),
            "independent_pin_present": bool(manifest["independent_pin_present"]),
            "network_identity_recovery_present": bool(manifest["network_identity_recovery_present"]),
            "raw_private_keys_exposed": False,
        }

    def restore_backup(
        self,
        source: str | Path,
        *,
        password: str,
        actor_id: str,
        confirmation: str,
        acknowledge_replace_existing: bool = False,
    ) -> dict[str, Any]:
        if confirmation != "RESTORE COMPLETE LEGAL AND GLYPHCHAIN STATE":
            raise LegalFullStateBackupError("full_state_restore_confirmation_required")
        self._validate_password(password)
        actor = " ".join(str(actor_id or "").split()).strip()[:160]
        if not actor:
            raise LegalFullStateBackupError("full_state_restore_actor_required")
        source_path = Path(source).expanduser().resolve()
        with tempfile.TemporaryDirectory(prefix="tessaris-full-state-restore-") as temporary:
            temporary_root = Path(temporary)
            archive = temporary_root / "payload.zip"
            header = self._decrypt_archive(source_path, archive, password=password)
            manifest = self._validate_zip(archive)
            self._assert_header_manifest(header, manifest)
            extracted = temporary_root / "extracted"
            self._extract_verified(archive, extracted, manifest)
            recovery = json.loads((extracted / "recovery" / "key-recovery.json").read_text(encoding="utf-8"))
            self._preflight_recovery(recovery, password=password, temporary_root=temporary_root)
            targets = self._restore_targets(extracted, manifest)
            occupied = [str(target) for _, target in targets if self._path_has_content(target)]
            if occupied and not acknowledge_replace_existing:
                raise LegalFullStateBackupError("restore_target_not_empty:" + ",".join(occupied))
            safety_paths: list[dict[str, str]] = []
            installed: list[tuple[Path, Path | None]] = []
            try:
                for staged, target in targets:
                    safety = None
                    if target.exists():
                        safety = target.with_name(f"{target.name}.pre-restore-{manifest['backup_id']}")
                        if safety.exists():
                            raise LegalFullStateBackupError("restore_safety_path_already_exists")
                        os.replace(target, safety)
                        safety_paths.append({"target": str(target), "safety_copy": str(safety)})
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if staged.is_dir():
                        shutil.copytree(staged, target)
                        self._secure_tree(target)
                    else:
                        self._install_file(staged, target)
                    installed.append((target, safety))
                self._import_recovery(recovery, password=password)
                if not self._verify_recovery_audit():
                    raise LegalFullStateBackupError("restored_recovery_audit_chain_invalid")
                self._append_recovery_event(
                    "RESTORE_COMPLETED", backup_id=str(manifest["backup_id"]), actor_id=actor,
                    details={"replaced_existing": bool(occupied)},
                )
                restored_state = self._verify_restored_state()
            except Exception:
                for target, safety in reversed(installed):
                    if target.is_dir():
                        shutil.rmtree(target, ignore_errors=True)
                    else:
                        target.unlink(missing_ok=True)
                    if safety and safety.exists():
                        os.replace(safety, target)
                raise
        return {
            "restored": True,
            "verified": True,
            "backup_id": manifest["backup_id"],
            "workspace_id": manifest["workspace_id"],
            "chain_id": manifest["chain_id"],
            "node_id": manifest["node_id"],
            "file_count": len(manifest["files"]),
            "safety_copies": safety_paths,
            "restored_state": restored_state,
            "restart_required": True,
            "raw_private_keys_exposed": False,
        }

    @property
    def _recovery_audit_path(self) -> Path:
        return self.layout.glyphchain_state_root / "device-recovery-audit.jsonl"

    def _append_recovery_event(
        self,
        event_type: str,
        *,
        backup_id: str,
        actor_id: str,
        details: Mapping[str, Any],
    ) -> None:
        path = self._recovery_audit_path
        path.parent.mkdir(parents=True, exist_ok=True)
        events = self._read_recovery_audit()
        if events and not self._verify_recovery_audit(events):
            raise LegalFullStateBackupError("device_recovery_audit_chain_invalid")
        core = {
            "sequence": len(events) + 1,
            "event_id": f"recovery-event-{uuid4().hex}",
            "event_type": str(event_type),
            "occurred_at": _utc_now(),
            "backup_id": str(backup_id),
            "actor_id": str(actor_id)[:160],
            "details": dict(details),
            "previous_hash": events[-1]["event_hash"] if events else "GENESIS",
        }
        entry = {**core, "event_hash": sha256(_canonical(core)).hexdigest()}
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(path, 0o600)

    def _read_recovery_audit(self) -> list[dict[str, Any]]:
        path = self._recovery_audit_path
        if not path.exists():
            return []
        try:
            return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        except Exception as exc:
            raise LegalFullStateBackupError("device_recovery_audit_unreadable") from exc

    def _verify_recovery_audit(self, events: list[Mapping[str, Any]] | None = None) -> bool:
        previous = "GENESIS"
        for index, event in enumerate(events if events is not None else self._read_recovery_audit(), start=1):
            body = {key: value for key, value in dict(event).items() if key != "event_hash"}
            if int(body.get("sequence") or 0) != index or body.get("previous_hash") != previous:
                return False
            current = sha256(_canonical(body)).hexdigest()
            if not hmac.compare_digest(str(event.get("event_hash") or ""), current):
                return False
            previous = current
        return True

    @staticmethod
    def _validate_password(password: str) -> None:
        if len(str(password)) < 16:
            raise LegalFullStateBackupError("full_state_backup_password_minimum_16_characters")

    def _excluded_source_paths(self) -> set[Path]:
        excluded: set[Path] = set()
        for root in self.layout.legal_roots.values():
            excluded.add((Path(root) / "_secure_keys").resolve())
            excluded.add((Path(root) / "_key_metadata.json").resolve())
        excluded.add(
            (Path(self.layout.legal_roots["signing"]) / "_device_identity" / "legal-proof-ed25519.pem").resolve()
        )
        excluded.add(self.layout.network_identity_root.resolve())
        if self.layout.ledger_database:
            db = self.layout.ledger_database.resolve()
            excluded.update({db, Path(str(db) + "-wal"), Path(str(db) + "-shm")})
        if self.layout.checkpoint_path:
            excluded.add(self.layout.checkpoint_path.resolve())
        if self.layout.independent_pin_path:
            excluded.add(self.layout.independent_pin_path.resolve())
        return excluded

    def _copy_tree(self, source: Path, destination: Path, *, excluded: set[Path]) -> None:
        if not source.exists():
            destination.mkdir(parents=True, exist_ok=True)
            return
        if not source.is_dir() or source.is_symlink():
            raise LegalFullStateBackupError("backup_source_not_safe_directory")
        destination.mkdir(parents=True, exist_ok=True)
        count = 0
        for path in sorted(source.rglob("*")):
            resolved = path.resolve()
            if any(resolved == item or item in resolved.parents for item in excluded):
                continue
            if path.is_symlink():
                raise LegalFullStateBackupError("backup_source_contains_symlink")
            relative = path.relative_to(source)
            target = destination / relative
            if path.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not path.is_file():
                raise LegalFullStateBackupError("backup_source_contains_special_file")
            if path.stat().st_size > self.MAX_FILE_BYTES:
                raise LegalFullStateBackupError("backup_source_file_too_large")
            count += 1
            if count > self.MAX_FILES:
                raise LegalFullStateBackupError("backup_source_file_limit_exceeded")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)

    @staticmethod
    def _copy_optional_file(source: Path | None, destination: Path) -> None:
        if source is None or not source.exists():
            return
        if not source.is_file() or source.is_symlink():
            raise LegalFullStateBackupError("trust_material_not_safe_file")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    @staticmethod
    def _write_json_file(destination: Path, value: Mapping[str, Any]) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(_canonical(dict(value)))
        os.chmod(destination, 0o600)

    @staticmethod
    def _validate_copied_trust_material(root: Path) -> None:
        checkpoint_path = root / "validator-checkpoint.json"
        pin_path = root / "independent-pin.json"
        if not checkpoint_path.exists():
            if pin_path.exists():
                raise LegalFullStateBackupError("independent_pin_without_checkpoint")
            return
        try:
            from backend.modules.consensus.finality_checkpoint import normalize_checkpoint

            checkpoint = normalize_checkpoint(json.loads(checkpoint_path.read_text(encoding="utf-8")))
        except Exception as exc:
            raise LegalFullStateBackupError("backup_validator_checkpoint_invalid") from exc
        if not pin_path.exists():
            return
        try:
            pin = json.loads(pin_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise LegalFullStateBackupError("backup_independent_pin_invalid") from exc
        wanted_id = str(pin.get("checkpoint_id") or "").strip()
        wanted_root = str(pin.get("validator_set_root") or "").strip()
        if not wanted_id and not wanted_root:
            raise LegalFullStateBackupError("backup_independent_pin_value_missing")
        if wanted_id and not hmac.compare_digest(wanted_id, str(checkpoint["checkpoint_id"])):
            raise LegalFullStateBackupError("backup_independent_checkpoint_id_mismatch")
        if wanted_root and not hmac.compare_digest(wanted_root, str(checkpoint["validator_set_root"])):
            raise LegalFullStateBackupError("backup_independent_validator_root_mismatch")

    @staticmethod
    def _sqlite_backup(source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        source_connection = sqlite3.connect(f"file:{source.resolve()}?mode=ro", uri=True)
        destination_connection = sqlite3.connect(str(destination))
        try:
            source_connection.backup(destination_connection)
            result = destination_connection.execute("PRAGMA integrity_check").fetchone()
            if not result or str(result[0]).lower() != "ok":
                raise LegalFullStateBackupError("ledger_backup_integrity_check_failed")
        finally:
            destination_connection.close()
            source_connection.close()
        os.chmod(destination, 0o600)

    def _manifest_files(self, root: Path) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise LegalFullStateBackupError("backup_payload_contains_symlink")
            if not path.is_file():
                continue
            size = path.stat().st_size
            if size > self.MAX_FILE_BYTES:
                raise LegalFullStateBackupError("backup_payload_file_too_large")
            entries.append({
                "path": path.relative_to(root).as_posix(),
                "bytes": size,
                "sha256": _sha256_file(path),
            })
        if len(entries) > self.MAX_FILES:
            raise LegalFullStateBackupError("backup_payload_file_limit_exceeded")
        return entries

    @staticmethod
    def _write_zip(source: Path, destination: Path) -> None:
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in sorted(source.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(source).as_posix())

    @staticmethod
    def _derive_key(password: str, salt: bytes) -> bytes:
        return Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(str(password).encode("utf-8"))

    def _encrypt_archive(self, source: Path, destination: Path, *, password: str, header: Mapping[str, Any]) -> None:
        header_bytes = _canonical(dict(header))
        key = self._derive_key(password, base64.b64decode(str(header["salt_base64"]), validate=True))
        nonce_prefix = base64.b64decode(str(header["nonce_prefix_base64"]), validate=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        try:
            with source.open("rb") as raw, temporary.open("wb") as output:
                output.write(self.MAGIC)
                output.write(struct.pack(">I", len(header_bytes)))
                output.write(header_bytes)
                for index in range(int(header["chunk_count"])):
                    plaintext = raw.read(self.CHUNK_BYTES)
                    nonce = nonce_prefix + struct.pack(">I", index)
                    aad = header_bytes + struct.pack(">IQ", index, len(plaintext))
                    ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
                    output.write(struct.pack(">I", len(ciphertext)))
                    output.write(ciphertext)
                if raw.read(1):
                    raise LegalFullStateBackupError("backup_archive_changed_during_encryption")
                output.flush()
                os.fsync(output.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

    def _decrypt_archive(self, source: Path, destination: Path, *, password: str) -> dict[str, Any]:
        if not source.is_file() or source.is_symlink():
            raise LegalFullStateBackupError("full_state_backup_file_missing_or_unsafe")
        with source.open("rb") as stream:
            if stream.read(len(self.MAGIC)) != self.MAGIC:
                raise LegalFullStateBackupError("full_state_backup_magic_invalid")
            raw_length = stream.read(4)
            if len(raw_length) != 4:
                raise LegalFullStateBackupError("full_state_backup_header_missing")
            header_length = struct.unpack(">I", raw_length)[0]
            if header_length < 32 or header_length > 64 * 1024:
                raise LegalFullStateBackupError("full_state_backup_header_size_invalid")
            header_bytes = stream.read(header_length)
            if len(header_bytes) != header_length:
                raise LegalFullStateBackupError("full_state_backup_header_truncated")
            try:
                header = json.loads(header_bytes)
            except Exception:
                raise LegalFullStateBackupError("full_state_backup_header_invalid") from None
            self._validate_header(header)
            key = self._derive_key(password, base64.b64decode(header["salt_base64"], validate=True))
            nonce_prefix = base64.b64decode(header["nonce_prefix_base64"], validate=True)
            digest = sha256()
            written = 0
            try:
                with destination.open("wb") as output:
                    for index in range(int(header["chunk_count"])):
                        raw_chunk_length = stream.read(4)
                        if len(raw_chunk_length) != 4:
                            raise LegalFullStateBackupError("full_state_backup_chunk_truncated")
                        chunk_length = struct.unpack(">I", raw_chunk_length)[0]
                        if chunk_length < 16 or chunk_length > self.CHUNK_BYTES + 16:
                            raise LegalFullStateBackupError("full_state_backup_chunk_size_invalid")
                        ciphertext = stream.read(chunk_length)
                        if len(ciphertext) != chunk_length:
                            raise LegalFullStateBackupError("full_state_backup_chunk_truncated")
                        expected_plaintext = min(self.CHUNK_BYTES, int(header["archive_bytes"]) - written)
                        nonce = nonce_prefix + struct.pack(">I", index)
                        aad = header_bytes + struct.pack(">IQ", index, expected_plaintext)
                        plaintext = AESGCM(key).decrypt(nonce, ciphertext, aad)
                        if len(plaintext) != expected_plaintext:
                            raise LegalFullStateBackupError("full_state_backup_chunk_plaintext_size_invalid")
                        output.write(plaintext)
                        digest.update(plaintext)
                        written += len(plaintext)
                    if stream.read(1):
                        raise LegalFullStateBackupError("full_state_backup_trailing_data")
            except LegalFullStateBackupError:
                destination.unlink(missing_ok=True)
                raise
            except Exception:
                destination.unlink(missing_ok=True)
                raise PermissionError("Full-state backup could not be authenticated") from None
        if written != int(header["archive_bytes"]) or not hmac.compare_digest(digest.hexdigest(), header["archive_sha256"]):
            destination.unlink(missing_ok=True)
            raise LegalFullStateBackupError("full_state_backup_archive_digest_mismatch")
        return header

    def _validate_header(self, header: Mapping[str, Any]) -> None:
        if header.get("schema_version") != self.ENVELOPE_VERSION:
            raise LegalFullStateBackupError("full_state_backup_schema_unsupported")
        if header.get("kdf") != "scrypt-n32768-r8-p1" or header.get("cipher") != "AES-256-GCM-chunked":
            raise LegalFullStateBackupError("full_state_backup_crypto_policy_invalid")
        archive_bytes = int(header.get("archive_bytes") or 0)
        chunk_count = int(header.get("chunk_count") or 0)
        if archive_bytes <= 0 or archive_bytes > self.MAX_ARCHIVE_BYTES:
            raise LegalFullStateBackupError("full_state_backup_archive_size_invalid")
        if chunk_count != (archive_bytes + self.CHUNK_BYTES - 1) // self.CHUNK_BYTES:
            raise LegalFullStateBackupError("full_state_backup_chunk_count_invalid")
        if int(header.get("chunk_bytes") or 0) != self.CHUNK_BYTES:
            raise LegalFullStateBackupError("full_state_backup_chunk_policy_invalid")
        if len(str(header.get("archive_sha256") or "")) != 64:
            raise LegalFullStateBackupError("full_state_backup_archive_digest_invalid")
        if len(base64.b64decode(str(header.get("salt_base64") or ""), validate=True)) != 16:
            raise LegalFullStateBackupError("full_state_backup_salt_invalid")
        if len(base64.b64decode(str(header.get("nonce_prefix_base64") or ""), validate=True)) != 8:
            raise LegalFullStateBackupError("full_state_backup_nonce_invalid")

    @staticmethod
    def _assert_header_manifest(header: Mapping[str, Any], manifest: Mapping[str, Any]) -> None:
        for key in ("backup_id", "created_at"):
            if not hmac.compare_digest(str(header.get(key) or ""), str(manifest.get(key) or "")):
                raise LegalFullStateBackupError("full_state_backup_header_manifest_mismatch")

    def _validate_zip(self, archive_path: Path) -> dict[str, Any]:
        with zipfile.ZipFile(archive_path) as archive:
            infos = archive.infolist()
            if len(infos) > self.MAX_FILES + 1:
                raise LegalFullStateBackupError("full_state_backup_file_limit_exceeded")
            total = 0
            names: set[str] = set()
            for info in infos:
                path = PurePosixPath(info.filename)
                if path.is_absolute() or ".." in path.parts or not path.parts or info.filename in names:
                    raise LegalFullStateBackupError("full_state_backup_unsafe_archive_path")
                names.add(info.filename)
                if info.is_dir() or (info.external_attr >> 16) & 0o170000 == 0o120000:
                    raise LegalFullStateBackupError("full_state_backup_archive_special_entry")
                if info.file_size > self.MAX_FILE_BYTES or info.compress_size > self.MAX_FILE_BYTES:
                    raise LegalFullStateBackupError("full_state_backup_archive_entry_too_large")
                total += info.file_size
                if total > self.MAX_ARCHIVE_BYTES:
                    raise LegalFullStateBackupError("full_state_backup_expanded_size_limit_exceeded")
            if "manifest.json" not in names or "recovery/key-recovery.json" not in names:
                raise LegalFullStateBackupError("full_state_backup_required_files_missing")
            manifest = json.loads(archive.read("manifest.json"))
            if manifest.get("schema_version") != self.SCHEMA_VERSION:
                raise LegalFullStateBackupError("full_state_backup_manifest_invalid")
            expected = list(manifest.get("files") or [])
            if len(expected) > self.MAX_FILES:
                raise LegalFullStateBackupError("full_state_backup_manifest_file_limit_exceeded")
            if not hmac.compare_digest(str(manifest.get("files_sha256") or ""), sha256(_canonical(expected)).hexdigest()):
                raise LegalFullStateBackupError("full_state_backup_manifest_digest_invalid")
            listed = {str(item.get("path") or ""): item for item in expected}
            actual = names - {"manifest.json"}
            if set(listed) != actual:
                raise LegalFullStateBackupError("full_state_backup_manifest_members_mismatch")
            for name, item in listed.items():
                info = archive.getinfo(name)
                if int(item.get("bytes") or -1) != info.file_size:
                    raise LegalFullStateBackupError("full_state_backup_manifest_size_mismatch")
                digest = sha256()
                with archive.open(name) as stream:
                    while chunk := stream.read(1024 * 1024):
                        digest.update(chunk)
                if not hmac.compare_digest(str(item.get("sha256") or ""), digest.hexdigest()):
                    raise LegalFullStateBackupError("full_state_backup_manifest_hash_mismatch")
            return manifest

    @staticmethod
    def _extract_verified(archive_path: Path, destination: Path, manifest: Mapping[str, Any]) -> None:
        destination.mkdir(parents=True, exist_ok=False)
        with zipfile.ZipFile(archive_path) as archive:
            for item in manifest["files"]:
                relative = PurePosixPath(str(item["path"]))
                target = destination.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(str(relative)) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                os.chmod(target, 0o600)

    def _preflight_recovery(self, recovery: Mapping[str, Any], *, password: str, temporary_root: Path) -> None:
        if recovery.get("schema_version") != "tessaris.full-state-key-recovery.v1":
            raise LegalFullStateBackupError("full_state_key_recovery_invalid")
        for purpose in self.LEGAL_PURPOSES:
            LegalKeyStore(temporary_root / "preflight" / "legal" / purpose, runtime_mode="test").import_recovery_bundle(
                dict((recovery.get("legal") or {}).get(purpose) or {}), password,
            )
        network = recovery.get("network_identity")
        if network is not None:
            NetworkIdentityStore(
                temporary_root / "preflight" / "network-identity",
                chain_id=self.layout.chain_id,
                node_id=self.layout.node_id,
                runtime_mode="test",
            ).import_recovery_bundle(dict(network), password)

    def _restore_targets(self, extracted: Path, manifest: Mapping[str, Any]) -> list[tuple[Path, Path]]:
        if manifest.get("chain_id") != self.layout.chain_id or manifest.get("node_id") != self.layout.node_id:
            raise LegalFullStateBackupError("full_state_restore_network_identity_mismatch")
        targets: list[tuple[Path, Path]] = [
            (extracted / "legal" / purpose, Path(self.layout.legal_roots[purpose]))
            for purpose in self.LEGAL_PURPOSES
        ]
        targets.append((extracted / "glyphchain" / "state", self.layout.glyphchain_state_root))
        if bool(manifest.get("ledger_present")):
            if self.layout.ledger_database is None:
                raise LegalFullStateBackupError("full_state_restore_ledger_target_missing")
            targets.append((extracted / "glyphchain" / "ledger.sqlite3", self.layout.ledger_database))
        if bool(manifest.get("checkpoint_present")):
            checkpoint_target = self.layout.checkpoint_path or (
                self.layout.glyphchain_state_root / "restored-validator-checkpoint.json"
            )
            targets.append((extracted / "trust" / "validator-checkpoint.json", checkpoint_target))
        if bool(manifest.get("independent_pin_present")):
            pin_target = self.layout.independent_pin_path or (
                self.layout.glyphchain_state_root / "restored-independent-pin.json"
            )
            targets.append((extracted / "trust" / "independent-pin.json", pin_target))
        return targets

    @staticmethod
    def _path_has_content(path: Path) -> bool:
        if not path.exists():
            return False
        if path.is_file():
            return True
        return any(path.iterdir())

    def _install_file(self, staged: Path, target: Path) -> None:
        if self.layout.ledger_database and target.resolve() == self.layout.ledger_database.resolve():
            try:
                from backend.modules.chain_sim.chain_sim_ledger import (
                    install_verified_ledger_database,
                    persist_database_path,
                )
            except ImportError:
                persist_database_path = None
                install_verified_ledger_database = None
            if persist_database_path is not None and install_verified_ledger_database is not None:
                configured = persist_database_path()
                if configured is not None and configured.resolve() == target.resolve():
                    install_verified_ledger_database(staged, expected_sha256=_sha256_file(staged))
                    return
        shutil.copy2(staged, target)
        os.chmod(target, 0o600)

    def _import_recovery(self, recovery: Mapping[str, Any], *, password: str) -> None:
        for purpose in self.LEGAL_PURPOSES:
            LegalKeyStore(self.layout.legal_roots[purpose]).import_recovery_bundle(
                dict((recovery.get("legal") or {}).get(purpose) or {}), password,
            )
        network = recovery.get("network_identity")
        if network is not None:
            NetworkIdentityStore(
                self.layout.network_identity_root,
                chain_id=self.layout.chain_id,
                node_id=self.layout.node_id,
            ).import_recovery_bundle(dict(network), password)

    def _verify_restored_state(self) -> dict[str, Any]:
        from backend.modules.aion_business.runtime.legal_delivery_service import LegalDeliveryService
        from backend.modules.aion_business.runtime.legal_matter_service import LegalMatterService
        from backend.modules.aion_business.runtime.legal_secure_storage import LegalEncryptedStore
        from backend.modules.aion_business.runtime.legal_signing_service import LegalSigningService

        encrypted_records = 0
        for root in self.layout.legal_roots.values():
            key_store = LegalKeyStore(root)
            for path in Path(root).rglob("*.enc"):
                envelope = json.loads(path.read_text(encoding="utf-8"))
                purpose = str(envelope.get("purpose") or "")
                workspace_id = str(envelope.get("workspace_id") or "")
                record_id = str(envelope.get("record_id") or "")
                if not purpose or not workspace_id or not record_id:
                    raise LegalFullStateBackupError("restored_encrypted_record_header_invalid")
                LegalEncryptedStore(root, purpose=purpose, key_store=key_store).read(
                    path, workspace_id=workspace_id, record_id=record_id,
                )
                encrypted_records += 1

        signing = LegalSigningService(self.layout.legal_roots["signing"])
        signing_audits = 0
        delivery_audits = 0
        for folder in Path(self.layout.legal_roots["signing"]).iterdir():
            if not folder.is_dir() or folder.name.startswith("_"):
                continue
            workspace = folder.name
            for envelope in signing.list_envelopes(workspace):
                if not signing.verify_audit_chain(workspace, str(envelope["envelope_id"])):
                    raise LegalFullStateBackupError("restored_signing_audit_chain_invalid")
                signing_audits += 1
            delivery = LegalDeliveryService(self.layout.legal_roots["signing"])
            status = delivery.status(workspace)
            if status["items"] and not status["event_chains_valid"]:
                raise LegalFullStateBackupError("restored_delivery_event_chain_invalid")
            delivery_audits += len(status["items"])

        matters = LegalMatterService(self.layout.legal_roots["matters"])
        matter_audits = 0
        for folder in Path(self.layout.legal_roots["matters"]).iterdir():
            if not folder.is_dir() or folder.name.startswith("_"):
                continue
            workspace = folder.name
            for matter in matters.list_matters(workspace):
                if not matters.verify_audit_chain(workspace, str(matter["matter_id"])):
                    raise LegalFullStateBackupError("restored_matter_audit_chain_invalid")
                matter_audits += 1

        ledger_integrity = None
        if self.layout.ledger_database and self.layout.ledger_database.is_file():
            connection = sqlite3.connect(f"file:{self.layout.ledger_database.resolve()}?mode=ro", uri=True)
            try:
                row = connection.execute("PRAGMA integrity_check").fetchone()
                ledger_integrity = str(row[0]).lower() if row else "missing"
            finally:
                connection.close()
            if ledger_integrity != "ok":
                raise LegalFullStateBackupError("restored_ledger_integrity_check_failed")

        identity_valid = None
        if (self.layout.network_identity_root / "network-identity.json").is_file():
            identity_valid = NetworkIdentityStore(
                self.layout.network_identity_root,
                chain_id=self.layout.chain_id,
                node_id=self.layout.node_id,
            ).verify_rotation_chain()
            if not identity_valid:
                raise LegalFullStateBackupError("restored_network_identity_rotation_chain_invalid")
        return {
            "encrypted_records_authenticated": encrypted_records,
            "signing_audit_chains_verified": signing_audits,
            "matter_audit_chains_verified": matter_audits,
            "delivery_event_chains_verified": delivery_audits,
            "ledger_integrity": ledger_integrity,
            "network_identity_rotation_chain_valid": identity_valid,
        }

    @staticmethod
    def _secure_tree(root: Path) -> None:
        for path in [root, *root.rglob("*")]:
            if path.is_dir():
                os.chmod(path, 0o700)
            elif path.is_file():
                os.chmod(path, 0o600)
