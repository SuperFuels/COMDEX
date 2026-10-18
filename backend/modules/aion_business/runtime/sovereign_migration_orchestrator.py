"""Staged migration of one logical sovereign brain between customer-controlled targets."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict

from backend.modules.aion_business.runtime.sovereign_brain_setup import SovereignBrainSetup
from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_fabric.canonical import canonical_hash, utc_now_iso
from backend.modules.aion_fabric.identity import IdentityStore


class SovereignMigrationOrchestrator:
    """Export, restore, verify and activate; the source remains recoverable throughout."""

    def __init__(
        self, source_root: str | Path, journal_root: str | Path, *,
        domain_store: VaultDomainStore | None = None, workspace_id: str | None = None,
    ) -> None:
        self.source = SovereignBrainSetup(Path(source_root).resolve())
        self.journal_root = Path(journal_root).resolve()
        self.domain_store = domain_store
        if domain_store is None and guardian_mode_requested():
            runtime = configured_business_vault_runtime()
            self.domain_store = VaultDomainStore(
                runtime.guardian, actor_id="sovereign-migration-orchestrator"
            )
        self.workspace_id = None
        if self.domain_store is not None:
            resolved = workspace_id or self.domain_store.guardian.business_stable_id
            self.workspace_id = canonical_business_id(resolved)
        else:
            self.journal_root.mkdir(parents=True, exist_ok=True)

    def prepare(self, *, migration_id: str, target_kind: str, destination: str | Path,
                passphrase: str, actor_id: str, approval_ref: str) -> Dict[str, Any]:
        if target_kind not in {"aion_box", "customer_rack", "customer_private_cloud"}:
            raise ValueError("migration_target_kind_invalid")
        if len(passphrase) < 16 or not migration_id or not actor_id or not approval_ref:
            raise ValueError("migration_requirements_invalid")
        source_status = self.source.status()
        if not source_status.get("ok"):
            raise RuntimeError("source_brain_not_healthy")
        destination = Path(destination).resolve()
        if destination.exists() and any(destination.iterdir()):
            raise ValueError("migration_destination_must_be_empty")
        package = self.journal_root / f"{migration_id}.pilotmigration"
        export = self.source.create_complete_export(destination=package, passphrase=passphrase)
        public_key = IdentityStore(self.source.root / "identity").load_or_create().public_key_b64
        restored = SovereignBrainSetup.restore_complete_export(
            package=package, destination=destination, passphrase=passphrase, source_public_key=public_key
        )
        target_status = restored["brain_status"]
        if target_status["brain_id"] != source_status["brain_id"]:
            shutil.rmtree(destination, ignore_errors=True)
            raise RuntimeError("logical_brain_identity_changed")
        record = {
            "schema_version": "aion.sovereign_brain_migration.v1", "migration_id": migration_id,
            "brain_id": source_status["brain_id"], "target_kind": target_kind,
            "destination_hash": canonical_hash(str(destination)), "state": "verified_waiting_activation",
            "source_remains_active": True, "source_delete_permitted": False,
            "export_manifest_hash": export.get("manifest_hash") or export.get("archive_hash"),
            "target_health_hash": canonical_hash(target_status), "approved_by": actor_id,
            "approval_receipt_hash": canonical_hash(approval_ref), "prepared_at": utc_now_iso(),
        }
        self._write(migration_id, record)
        return record

    def activate(self, *, migration_id: str, destination: str | Path,
                 actor_id: str, activation_ref: str) -> Dict[str, Any]:
        record = self._read(migration_id)
        if record["state"] != "verified_waiting_activation":
            raise ValueError("migration_not_activatable")
        status = SovereignBrainSetup(Path(destination).resolve()).status()
        if not status.get("ok") or status.get("brain_id") != record["brain_id"]:
            raise RuntimeError("migration_target_health_or_identity_failed")
        record.update({"state": "target_active_source_retained", "activated_by": actor_id,
                       "activation_receipt_hash": canonical_hash(activation_ref),
                       "source_remains_recoverable": True, "activated_at": utc_now_iso()})
        self._write(migration_id, record)
        return record

    def rollback(self, *, migration_id: str, actor_id: str, reason: str) -> Dict[str, Any]:
        record = self._read(migration_id)
        if not actor_id or not reason:
            raise ValueError("rollback_actor_and_reason_required")
        record.update({"state": "rolled_back_to_source", "rolled_back_by": actor_id,
                       "rollback_reason_hash": canonical_hash(reason), "rolled_back_at": utc_now_iso()})
        self._write(migration_id, record)
        return record

    def _read(self, migration_id: str) -> Dict[str, Any]:
        if self.domain_store is not None:
            assert self.workspace_id is not None
            entity_id = f"sovereign-brain/migrations/{migration_id}"
            current = self.domain_store.get_optional(
                "vault.migration_receipts", workspace_id=self.workspace_id,
                entity_id=entity_id,
            )
            if current is not None:
                return dict(current["payload"])
            legacy_path = self.journal_root / f"{migration_id}.json"
            if legacy_path.is_file():
                payload = json.loads(legacy_path.read_text(encoding="utf-8"))
                self.domain_store.put(
                    "vault.migration_receipts", workspace_id=self.workspace_id,
                    entity_id=entity_id,
                    payload={**payload, "legacy_journal_copy_verified": True,
                             "legacy_journal_source_retained": True},
                    expected_version=None,
                    idempotency_key=f"sovereign-migration-import-{migration_id}",
                )
                return dict(self.domain_store.get(
                    "vault.migration_receipts", workspace_id=self.workspace_id,
                    entity_id=entity_id,
                )["payload"])
            raise KeyError("migration_not_found")
        path = self.journal_root / f"{migration_id}.json"
        if not path.exists():
            raise KeyError("migration_not_found")
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, migration_id: str, record: Dict[str, Any]) -> None:
        if self.domain_store is not None:
            assert self.workspace_id is not None
            entity_id = f"sovereign-brain/migrations/{migration_id}"
            current = self.domain_store.get_optional(
                "vault.migration_receipts", workspace_id=self.workspace_id,
                entity_id=entity_id,
            )
            self.domain_store.put(
                "vault.migration_receipts", workspace_id=self.workspace_id,
                entity_id=entity_id, payload=record,
                expected_version=int(current["version"]) if current else None,
            )
            return
        path = self.journal_root / f"{migration_id}.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
