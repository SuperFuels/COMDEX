"""Source-retaining legacy import and encrypted whole-business customer export.

This boundary deliberately separates two different jobs:

* a legacy source is inspected, copied into Guardian, read back and receipted;
  the source is never renamed, truncated or deleted; and
* a portable customer export contains every live Guardian head plus every
  decrypted original, but the complete payload is encrypted before it leaves
  the customer-controlled staging boundary.

The portable export is a transfer artefact, not the forensic backup used by
``VaultSnapshotService``.  Journey 26 separately proves immutable history,
interruption and disaster restore.
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from typing import Any, Mapping

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from backend.modules.aion_business.runtime.business_data_domain_registry import (
    BusinessDataDomainRegistry,
)
from backend.modules.aion_business.runtime.business_vault_runtime import BusinessVaultRuntime
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore


TRANSFER_SCHEMA = "tessaris.business-portable-export.v1"
LEGACY_IMPORT_SCHEMA = "tessaris.legacy-business-import.v1"
SAFE_ID_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
REQUIRED_TRANSFER_DOMAINS = frozenset(
    {
        "business.map",
        "departments.map",
        "train_agent.automations",
        "file_cabinet.tree",
        "file_cabinet.originals",
        "file_cabinet.governance",
    }
)


class BusinessVaultPortableTransferError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _safe_id(value: str, field: str) -> str:
    result = str(value or "").strip()
    if not result or len(result) > 120 or any(char not in SAFE_ID_CHARS for char in result):
        raise BusinessVaultPortableTransferError(f"{field}_invalid")
    return result


def _within(candidate: Path, parent: Path) -> bool:
    try:
        candidate.resolve(strict=False).relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


def _atomic_private_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    value = str(passphrase or "")
    if len(value) < 16:
        raise BusinessVaultPortableTransferError("export_passphrase_too_short")
    return Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(value.encode("utf-8"))


class LegacyBusinessImportService:
    """Import the bounded legacy transfer layout without mutating its source."""

    def __init__(
        self,
        runtime: BusinessVaultRuntime,
        *,
        domain_store: VaultDomainStore | None = None,
        actor_id: str = "legacy-business-import",
    ) -> None:
        self.runtime = runtime
        self.store = domain_store or VaultDomainStore(runtime.guardian, actor_id=actor_id)
        self.actor_id = actor_id

    @staticmethod
    def _source_files(source_root: Path) -> list[Path]:
        if not source_root.is_dir() or source_root.is_symlink():
            raise BusinessVaultPortableTransferError("legacy_source_directory_invalid")
        files: list[Path] = []
        for path in sorted(source_root.rglob("*")):
            if path.is_symlink():
                raise BusinessVaultPortableTransferError("legacy_source_symlink_forbidden")
            if path.is_file():
                files.append(path)
        return files

    @classmethod
    def _source_digest(cls, source_root: Path) -> str:
        digest = hashlib.sha256()
        for path in cls._source_files(source_root):
            relative = path.relative_to(source_root).as_posix().encode("utf-8")
            raw = path.read_bytes()
            digest.update(len(relative).to_bytes(8, "big"))
            digest.update(relative)
            digest.update(len(raw).to_bytes(8, "big"))
            digest.update(raw)
        return digest.hexdigest()

    @staticmethod
    def _read_json(path: Path, field: str) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise BusinessVaultPortableTransferError(f"legacy_{field}_invalid") from exc
        if not isinstance(value, dict):
            raise BusinessVaultPortableTransferError(f"legacy_{field}_invalid")
        return value

    def inspect(self, *, source_root: str | Path, migration_id: str) -> dict[str, Any]:
        migration_id = _safe_id(migration_id, "migration_id")
        source = Path(source_root).expanduser().resolve(strict=True)
        if _within(source, self.runtime.layout.root):
            raise BusinessVaultPortableTransferError("legacy_source_inside_business_vault")
        required = {
            "business_map": source / "business_map.json",
            "departments_map": source / "departments_map.json",
            "automations": source / "automations.json",
        }
        missing = sorted(name for name, path in required.items() if not path.is_file())
        if missing:
            raise BusinessVaultPortableTransferError(
                "legacy_required_files_missing:" + ",".join(missing)
            )
        originals_root = source / "originals"
        originals = [] if not originals_root.exists() else [
            path for path in self._source_files(originals_root)
        ]
        if not originals:
            raise BusinessVaultPortableTransferError("legacy_originals_required")
        documents = {name: self._read_json(path, name) for name, path in required.items()}
        return {
            "schema_version": LEGACY_IMPORT_SCHEMA,
            "migration_id": migration_id,
            "mode": "dry_run",
            "source_sha256": self._source_digest(source),
            "candidate_domains": sorted(REQUIRED_TRANSFER_DOMAINS),
            "record_candidate_count": len(documents),
            "original_candidate_count": len(originals),
            "source_retained": True,
            "source_delete_permitted": False,
            "ready": True,
            "_source": source,
            "_documents": documents,
            "_originals": originals,
        }

    def execute(
        self,
        *,
        workspace_id: str,
        source_root: str | Path,
        migration_id: str,
    ) -> dict[str, Any]:
        workspace_id = _safe_id(workspace_id, "workspace_id")
        inspected = self.inspect(source_root=source_root, migration_id=migration_id)
        migration_id = inspected["migration_id"]
        receipt_entity = f"legacy-import-{migration_id}"
        existing = self.store.get_optional(
            "vault.migration_receipts",
            workspace_id=workspace_id,
            entity_id=receipt_entity,
        )
        if existing is not None:
            receipt = dict(existing["payload"])
            if receipt.get("source_sha256") != inspected["source_sha256"]:
                raise BusinessVaultPortableTransferError("legacy_import_replay_source_changed")
            return {**receipt, "idempotent_replay": True}

        source = inspected["_source"]
        documents = inspected["_documents"]
        entity_prefix = f"migration-{migration_id}"
        targets = (
            ("business.map", f"{entity_prefix}-business-map", documents["business_map"]),
            ("departments.map", f"{entity_prefix}-departments-map", documents["departments_map"]),
            ("train_agent.automations", f"{entity_prefix}-automations", documents["automations"]),
        )
        verified_records: list[dict[str, str]] = []
        for domain_id, entity_id, payload in targets:
            self.store.put(
                domain_id,
                workspace_id=workspace_id,
                entity_id=entity_id,
                payload=payload,
                expected_version=None,
                idempotency_key=f"{entity_prefix}-{domain_id.replace('.', '-')}",
                actor_id=self.actor_id,
            )
            copied = self.store.get(
                domain_id, workspace_id=workspace_id, entity_id=entity_id
            )["payload"]
            if _sha256(_canonical(copied)) != _sha256(_canonical(payload)):
                raise RuntimeError(f"legacy_import_readback_failed:{domain_id}")
            verified_records.append(
                {"domain_id": domain_id, "entity_id": entity_id, "sha256": _sha256(_canonical(payload))}
            )

        tree_record = self.store.get_optional(
            "file_cabinet.tree", workspace_id=workspace_id, entity_id="tree"
        )
        if tree_record is None:
            tree: dict[str, Any] = {
                "schema_version": "aion.workflow_file_cabinet.v1",
                "workspace_id": workspace_id,
                "root": {"id": "root", "type": "folder", "name": "Business Files", "children": []},
            }
            tree_version = None
        else:
            tree = dict(tree_record["payload"])
            tree_version = int(tree_record["version"])
        root = tree.setdefault(
            "root", {"id": "root", "type": "folder", "name": "Business Files", "children": []}
        )
        children = root.setdefault("children", [])
        imported_folder = {
            "id": f"import-{migration_id}",
            "type": "folder",
            "name": f"Imported {migration_id}",
            "children": [],
        }
        object_proofs: list[dict[str, Any]] = []
        for index, path in enumerate(inspected["_originals"], start=1):
            raw = path.read_bytes()
            relative_name = path.relative_to(source / "originals").as_posix()
            object_id = f"migration-{_sha256((migration_id + relative_name).encode())[:32]}"
            sys.audit("tessaris.vault_domain_access", "file_cabinet.originals", "put")
            metadata = self.runtime.objects.put_bytes(
                object_id=object_id,
                data=raw,
                original_name=path.name,
                content_type="application/octet-stream",
                idempotency_key=f"legacy-{migration_id}-{index}",
                actor_id=self.actor_id,
                recorded_at=_now(),
            )
            _, readback = self.runtime.objects.get_bytes(object_id=object_id)
            if readback != raw:
                raise RuntimeError("legacy_original_readback_failed")
            imported_folder["children"].append(
                {
                    "id": f"import-item-{migration_id}-{index}",
                    "type": "artifact",
                    "name": relative_name,
                    "status": "active",
                    "source_of_truth": "business_vault",
                    "target": {"vault_object_id": object_id},
                }
            )
            object_proofs.append(
                {"object_id": object_id, "plaintext_sha256": metadata["plaintext_sha256"], "byte_length": len(raw)}
            )
            self.store.put(
                "file_cabinet.governance",
                workspace_id=workspace_id,
                entity_id=f"legacy-import-{migration_id}-{index}",
                payload={
                    "schema_version": "aion.file_cabinet_governance.v1",
                    "operation": "legacy_original_imported",
                    "migration_id": migration_id,
                    "item_id": f"import-item-{migration_id}-{index}",
                    "object_sha256": metadata["plaintext_sha256"],
                    "source_retained": True,
                    "recorded_at": _now(),
                },
                expected_version=None,
                idempotency_key=f"legacy-governance-{migration_id}-{index}",
                actor_id=self.actor_id,
            )
        children.append(imported_folder)
        tree["folders"] = children
        self.store.put(
            "file_cabinet.tree",
            workspace_id=workspace_id,
            entity_id="tree",
            payload=tree,
            expected_version=tree_version,
            idempotency_key=f"legacy-tree-{migration_id}",
            actor_id=self.actor_id,
        )

        after_digest = self._source_digest(source)
        if after_digest != inspected["source_sha256"]:
            raise RuntimeError("legacy_source_changed_during_import")
        receipt = {
            "schema_version": LEGACY_IMPORT_SCHEMA,
            "migration_id": migration_id,
            "workspace_id": workspace_id,
            "source_sha256": after_digest,
            "source_retained": True,
            "source_delete_permitted": False,
            "verified_record_count": len(verified_records),
            "verified_original_count": len(object_proofs),
            "verified_records": verified_records,
            "verified_originals": object_proofs,
            "state": "copied_verified_source_retained",
            "completed_at": _now(),
            "idempotent_replay": False,
        }
        self.store.put(
            "vault.migration_receipts",
            workspace_id=workspace_id,
            entity_id=receipt_entity,
            payload=receipt,
            expected_version=None,
            idempotency_key=f"legacy-receipt-{migration_id}",
            actor_id=self.actor_id,
        )
        return receipt


class BusinessVaultPortableExportService:
    """Create and verify one passphrase-encrypted current-state export."""

    def __init__(self, runtime: BusinessVaultRuntime) -> None:
        self.runtime = runtime

    def _collections(self) -> list[str]:
        with sqlite3.connect(self.runtime.guardian.database) as connection:
            rows = connection.execute(
                "SELECT DISTINCT collection FROM guardian_record_heads ORDER BY collection"
            ).fetchall()
        return [str(row[0]) for row in rows]

    def _payload(self, workspace_id: str, export_id: str, created_at: str) -> dict[str, Any]:
        records: list[dict[str, Any]] = []
        domains: set[str] = set()
        for collection in self._collections():
            for record in self.runtime.guardian.list_records(collection=collection):
                payload = record["payload"]
                if isinstance(payload, dict) and payload.get("schema_version") == "tessaris.vault-domain-record.v1":
                    if str(payload.get("workspace_id")) != workspace_id:
                        continue
                    domain_id = str(payload.get("domain_id") or "")
                    if domain_id:
                        domains.add(domain_id)
                records.append(
                    {
                        "collection": collection,
                        "record_id": record["record_id"],
                        "version": record["version"],
                        "recorded_at": record["recorded_at"],
                        "plaintext_sha256": record["plaintext_sha256"],
                        "payload": payload,
                    }
                )

        objects: list[dict[str, Any]] = []
        for record in self.runtime.guardian.list_records(collection="original_files"):
            object_id = str(record["record_id"])
            metadata, raw = self.runtime.objects.get_bytes(object_id=object_id)
            objects.append(
                {
                    "object_id": object_id,
                    "original_name": metadata["original_name"],
                    "content_type": metadata["content_type"],
                    "byte_length": len(raw),
                    "plaintext_sha256": _sha256(raw),
                    "data_base64": base64.b64encode(raw).decode("ascii"),
                }
            )
        if objects:
            domains.add("file_cabinet.originals")
        coverage = {domain_id: domain_id in domains for domain_id in sorted(REQUIRED_TRANSFER_DOMAINS)}
        missing = [domain_id for domain_id, present in coverage.items() if not present]
        if missing:
            raise BusinessVaultPortableTransferError(
                "portable_export_required_coverage_missing:" + ",".join(missing)
            )
        manifest = {
            "schema_version": TRANSFER_SCHEMA,
            "export_id": export_id,
            "business_stable_id": self.runtime.guardian.business_stable_id,
            "workspace_id": workspace_id,
            "created_at": created_at,
            "record_count": len(records),
            "original_count": len(objects),
            "domain_ids": sorted(domains),
            "required_coverage": coverage,
            "includes_maps": True,
            "includes_departments": True,
            "includes_automations": True,
            "includes_originals": True,
            "customer_content_in_cleartext": False,
        }
        return {"manifest": manifest, "records": records, "originals": objects}

    def create_export(
        self,
        *,
        workspace_id: str,
        export_id: str,
        destination_root: str | Path,
        passphrase: str,
        created_at: str | None = None,
    ) -> Path:
        workspace_id = _safe_id(workspace_id, "workspace_id")
        export_id = _safe_id(export_id, "export_id")
        destination = Path(destination_root).expanduser().resolve(strict=False)
        if _within(destination, self.runtime.layout.root) or _within(self.runtime.layout.root, destination):
            raise BusinessVaultPortableTransferError("portable_export_vault_overlap")
        destination.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = destination / f"{export_id}.tessaris-export"
        if target.exists():
            existing = self.readback(export_path=target, passphrase=passphrase)
            manifest = existing.get("manifest") or {}
            if (
                manifest.get("export_id") != export_id
                or manifest.get("workspace_id") != workspace_id
                or manifest.get("business_stable_id")
                != self.runtime.guardian.business_stable_id
            ):
                raise BusinessVaultPortableTransferError(
                    "portable_export_existing_identity_mismatch"
                )
            return target
        created = created_at or _now()
        payload = self._payload(workspace_id, export_id, created)
        raw = _canonical(payload)
        salt = os.urandom(16)
        nonce = os.urandom(12)
        aad = _canonical(
            {"schema_version": TRANSFER_SCHEMA, "export_id": export_id, "business_stable_id": self.runtime.guardian.business_stable_id}
        )
        ciphertext = AESGCM(_derive_key(passphrase, salt)).encrypt(nonce, raw, aad)
        envelope = {
            "schema_version": TRANSFER_SCHEMA,
            "export_id": export_id,
            "business_stable_id": self.runtime.guardian.business_stable_id,
            "encryption": "scrypt-aes-256-gcm",
            "salt_base64": base64.b64encode(salt).decode("ascii"),
            "nonce_base64": base64.b64encode(nonce).decode("ascii"),
            "ciphertext_base64": base64.b64encode(ciphertext).decode("ascii"),
            "ciphertext_sha256": _sha256(ciphertext),
            "key_material_in_export": False,
        }
        _atomic_private_json(target, envelope)
        return target

    @staticmethod
    def readback(*, export_path: str | Path, passphrase: str) -> dict[str, Any]:
        path = Path(export_path).expanduser().resolve(strict=True)
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
            if envelope.get("schema_version") != TRANSFER_SCHEMA:
                raise BusinessVaultPortableTransferError("portable_export_schema_invalid")
            salt = base64.b64decode(envelope["salt_base64"], validate=True)
            nonce = base64.b64decode(envelope["nonce_base64"], validate=True)
            ciphertext = base64.b64decode(envelope["ciphertext_base64"], validate=True)
        except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
            if isinstance(exc, BusinessVaultPortableTransferError):
                raise
            raise BusinessVaultPortableTransferError("portable_export_envelope_invalid") from exc
        if _sha256(ciphertext) != envelope.get("ciphertext_sha256"):
            raise BusinessVaultPortableTransferError("portable_export_ciphertext_integrity_failed")
        aad = _canonical(
            {
                "schema_version": TRANSFER_SCHEMA,
                "export_id": envelope["export_id"],
                "business_stable_id": envelope["business_stable_id"],
            }
        )
        try:
            payload = json.loads(
                AESGCM(_derive_key(passphrase, salt)).decrypt(nonce, ciphertext, aad)
            )
        except Exception as exc:
            raise BusinessVaultPortableTransferError("portable_export_decryption_failed") from exc
        manifest = payload.get("manifest") or {}
        if manifest.get("export_id") != envelope.get("export_id"):
            raise BusinessVaultPortableTransferError("portable_export_identity_mismatch")
        for record in payload.get("records") or []:
            if _sha256(_canonical(record.get("payload"))) != record.get("plaintext_sha256"):
                raise BusinessVaultPortableTransferError("portable_export_record_integrity_failed")
        for item in payload.get("originals") or []:
            raw = base64.b64decode(item.get("data_base64") or "", validate=True)
            if len(raw) != int(item.get("byte_length") or -1) or _sha256(raw) != item.get("plaintext_sha256"):
                raise BusinessVaultPortableTransferError("portable_export_original_integrity_failed")
        return payload

    @staticmethod
    def summary(payload: Mapping[str, Any]) -> dict[str, Any]:
        manifest = dict(payload.get("manifest") or {})
        originals = list(payload.get("originals") or [])
        return {
            "manifest": manifest,
            "original_count": len(originals),
            "originals_manifest_sha256": _sha256(
                _canonical(
                    [
                        {
                            "byte_length": item["byte_length"],
                            "plaintext_sha256": item["plaintext_sha256"],
                        }
                        for item in originals
                    ]
                )
            ),
            "all_originals_verified": len(originals) == int(manifest.get("original_count") or -1),
            "verified": True,
            "customer_content_in_response": False,
        }
