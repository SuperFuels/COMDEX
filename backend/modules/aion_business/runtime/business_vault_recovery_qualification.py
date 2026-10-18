"""Content-free disaster-recovery qualification for one Business Vault."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
from typing import Any

from backend.modules.aion_business.runtime.business_vault_runtime import BusinessVaultRuntime
from backend.modules.aion_business.runtime.business_data_domain_registry import (
    BusinessDataDomainRegistry,
    PROTECTED_CONTINUITY_SURFACE_DOMAINS,
    REQUIRED_DEPARTMENT_VAULT_DOMAINS,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_business.runtime.vault_object_store import VaultObjectStore
from backend.modules.aion_business.runtime.vault_snapshot import VaultSnapshotError, VaultSnapshotService


RECOVERY_SCHEMA = "tessaris.business-vault-recovery-drill.v1"
PROTECTED_CONTINUITY_DOMAINS = tuple(sorted(
    set(REQUIRED_DEPARTMENT_VAULT_DOMAINS).union(
        *(set(domains) for domains in PROTECTED_CONTINUITY_SURFACE_DOMAINS.values())
    )
))


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _inventory(database: Path) -> dict[str, Any]:
    with sqlite3.connect(database) as connection:
        heads = connection.execute(
            """
            SELECT v.collection, v.record_id, v.version, v.plaintext_sha256, v.tombstone
            FROM guardian_record_versions v
            JOIN guardian_record_heads h
              ON h.collection=v.collection AND h.record_id=v.record_id AND h.version=v.version
            ORDER BY v.collection, v.record_id
            """
        ).fetchall()
        history_count = int(
            connection.execute("SELECT COUNT(*) FROM guardian_record_versions").fetchone()[0]
        )
        receipt_count = int(
            connection.execute("SELECT COUNT(*) FROM guardian_audit_receipts").fetchone()[0]
        )
    canonical_heads = [
        [str(row[0]), str(row[1]), int(row[2]), str(row[3]), int(row[4])] for row in heads
    ]
    original_heads = [row for row in canonical_heads if row[0] == "original_files" and row[4] == 0]
    return {
        "live_head_count": sum(1 for row in canonical_heads if row[4] == 0),
        "tombstoned_head_count": sum(1 for row in canonical_heads if row[4] == 1),
        "history_version_count": history_count,
        "audit_receipt_count": receipt_count,
        "original_count": len(original_heads),
        "heads_sha256": _sha256(_canonical(canonical_heads)),
        "original_heads_sha256": _sha256(_canonical(original_heads)),
    }


class BusinessVaultRecoveryQualificationService:
    """Create, damage, restore and prove a snapshot without touching the live Vault."""

    def __init__(
        self,
        runtime: BusinessVaultRuntime,
        *,
        vault_encryption_key: bytes,
        snapshot_encryption_key: bytes,
        staging_root: str | Path,
        business_stable_id: str,
        actor_id: str = "business-vault-recovery-drill",
    ) -> None:
        if len(vault_encryption_key) != 32 or len(snapshot_encryption_key) != 32:
            raise ValueError("recovery_qualification_key_invalid")
        self.runtime = runtime
        self.vault_key = bytes(vault_encryption_key)
        self.snapshot_key = bytes(snapshot_encryption_key)
        self.root = Path(staging_root).expanduser().resolve(strict=False)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)
        self.business_stable_id = business_stable_id
        self.actor_id = actor_id
        self.store = VaultDomainStore(runtime.guardian, actor_id=actor_id)

    def _snapshot_plaintext_absent(
        self, snapshot: Path, restored_objects: VaultObjectStore
    ) -> tuple[bool, int]:
        needles: list[bytes] = []
        for record in restored_objects.guardian.list_records(collection="original_files"):
            _, raw = restored_objects.get_bytes(object_id=record["record_id"])
            if len(raw) >= 16:
                needles.append(raw)
        for domain_id in PROTECTED_CONTINUITY_DOMAINS:
            if domain_id == "file_cabinet.originals":
                continue
            for record in VaultDomainStore(restored_objects.guardian).list_all(domain_id):
                raw = _canonical(record["payload"])
                if len(raw) >= 16:
                    needles.append(raw)
        checked = 0
        for path in snapshot.rglob("*"):
            if not path.is_file():
                continue
            sealed = path.read_bytes()
            for needle in needles:
                checked += 1
                if needle in sealed:
                    return False, checked
        return True, checked

    @staticmethod
    def _simulate_corruption(restored_root: Path, corrupt_root: Path) -> bool:
        shutil.rmtree(corrupt_root, ignore_errors=True)
        shutil.copytree(restored_root, corrupt_root)
        database = corrupt_root / "records" / "guardian.sqlite3"
        raw = database.read_bytes()
        database.write_bytes(raw[: max(128, len(raw) // 3)])
        try:
            with sqlite3.connect(database) as connection:
                result = connection.execute("PRAGMA integrity_check").fetchone()
                return not result or str(result[0]).lower() != "ok"
        except sqlite3.DatabaseError:
            return True

    def run(self, *, workspace_id: str, snapshot_id: str) -> dict[str, Any]:
        receipt_entity = f"recovery-drill-{snapshot_id}"
        prior = self.store.get_optional(
            "vault.migration_receipts", workspace_id=workspace_id, entity_id=receipt_entity
        )
        if prior is not None:
            return {**dict(prior["payload"]), "idempotent_replay": True}

        snapshot_service = VaultSnapshotService(
            self.runtime.layout, encryption_key=self.snapshot_key
        )
        backup_root = self.root / "backup-destination"
        snapshot = snapshot_service.create_snapshot(
            destination_root=backup_root, snapshot_id=snapshot_id, created_at=_now()
        )
        inspected = snapshot_service.inspect_snapshot(snapshot_path=snapshot)
        restored_root = self.root / "clean-restored-vault"
        shutil.rmtree(restored_root, ignore_errors=True)
        restored_layout = snapshot_service.restore_snapshot(
            snapshot_path=snapshot, destination_root=restored_root
        )
        restored_guardian = VaultGuardian(
            restored_layout,
            business_stable_id=self.business_stable_id,
            encryption_key=self.vault_key,
        )
        restored_objects = VaultObjectStore(
            restored_layout,
            guardian=restored_guardian,
            business_stable_id=self.business_stable_id,
            encryption_key=self.vault_key,
        )
        inventory = _inventory(restored_guardian.database)
        chain = restored_guardian.verify_audit_chain()
        if not chain.get("healthy"):
            raise RuntimeError("restored_guardian_audit_unhealthy")

        snapshot_entries = {entry["relative_path"]: entry for entry in inspected["entries"]}
        restored_entries: list[list[Any]] = []
        for relative_path, entry in sorted(snapshot_entries.items()):
            path = restored_root / relative_path
            if not path.is_file():
                raise RuntimeError("restored_snapshot_entry_missing")
            raw = path.read_bytes()
            if len(raw) != entry["byte_length"] or _sha256(raw) != entry["plaintext_sha256"]:
                raise RuntimeError("restored_snapshot_entry_mismatch")
            restored_entries.append([relative_path, len(raw), _sha256(raw)])

        registered_domain_counts: dict[str, int] = {}
        restored_store = VaultDomainStore(restored_guardian, actor_id=self.actor_id)
        registry = BusinessDataDomainRegistry()
        for domain_id in sorted(registry.manifest()):
            registered_domain_counts[domain_id] = len(restored_store.list_all(domain_id))
        sys.audit("tessaris.vault_domain_access", "file_cabinet.originals", "recovery_verify")
        protected_domain_counts = {
            domain_id: (
                inventory["original_count"]
                if domain_id == "file_cabinet.originals"
                else registered_domain_counts[domain_id]
            )
            for domain_id in PROTECTED_CONTINUITY_DOMAINS
        }

        plaintext_absent, plaintext_probe_count = self._snapshot_plaintext_absent(
            snapshot, restored_objects
        )
        if not plaintext_absent:
            raise RuntimeError("snapshot_contains_customer_plaintext")
        corrupt_detected = self._simulate_corruption(
            restored_root, self.root / "corrupt-live-copy"
        )
        if not corrupt_detected:
            raise RuntimeError("corrupt_copy_not_detected")
        try:
            snapshot_service.restore_snapshot(
                snapshot_path=snapshot, destination_root=self.runtime.layout.root
            )
        except VaultSnapshotError as exc:
            live_overwrite_refused = str(exc) == "restore_destination_not_empty"
        else:
            live_overwrite_refused = False
        if not live_overwrite_refused:
            raise RuntimeError("live_vault_overwrite_not_refused")

        result = {
            "schema_version": RECOVERY_SCHEMA,
            "snapshot_id": snapshot_id,
            "workspace_id": workspace_id,
            "snapshot_encryption": inspected["encryption"],
            "snapshot_index_sha256": inspected["index_sha256"],
            "snapshot_entry_count": len(snapshot_entries),
            "snapshot_entries_sha256": _sha256(_canonical(restored_entries)),
            "key_material_in_snapshot": inspected["key_material_in_snapshot"],
            "snapshot_plaintext_absent": True,
            "plaintext_probe_count": plaintext_probe_count,
            "corrupt_copy_detected": True,
            "restored_to_separate_clean_root": restored_root != self.runtime.layout.root,
            "live_vault_overwrite_refused": True,
            "snapshot_restore_hashes_match": True,
            "guardian_audit_healthy": True,
            "domain_counts": protected_domain_counts,
            "protected_continuity_domain_counts": protected_domain_counts,
            "registered_domain_counts": registered_domain_counts,
            "registered_domain_count": len(registered_domain_counts),
            "complete_registry_readback": (
                len(registered_domain_counts) == len(registry.manifest())
            ),
            "inventory": inventory,
            "completed_at": _now(),
            "state": "snapshot_restored_and_verified",
            "customer_content_in_receipt": False,
            "idempotent_replay": False,
        }
        self.store.put(
            "vault.migration_receipts",
            workspace_id=workspace_id,
            entity_id=receipt_entity,
            payload=result,
            expected_version=None,
            idempotency_key=f"recovery-migration-{snapshot_id}",
            actor_id=self.actor_id,
        )
        self.store.put(
            "security.audit",
            workspace_id=workspace_id,
            entity_id=receipt_entity,
            payload={
                "schema_version": RECOVERY_SCHEMA,
                "event": "business_vault_recovery_drill_completed",
                "snapshot_id": snapshot_id,
                "snapshot_index_sha256": inspected["index_sha256"],
                "inventory_sha256": inventory["heads_sha256"],
                "corrupt_copy_detected": True,
                "live_vault_overwrite_refused": True,
                "recorded_at": result["completed_at"],
            },
            expected_version=None,
            idempotency_key=f"recovery-security-{snapshot_id}",
            actor_id=self.actor_id,
        )
        return result
