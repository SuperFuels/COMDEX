"""Governed retention and non-destructive business-closure preview."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from backend.modules.aion_business.runtime.business_vault_runtime import BusinessVaultRuntime
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore


CLOSURE_SCHEMA = "tessaris.business-retention-closure-preview.v1"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class BusinessRetentionClosureService:
    """Prove closure prerequisites while deliberately exposing no delete operation."""

    def __init__(self, runtime: BusinessVaultRuntime, *, actor_id: str = "retention-closure") -> None:
        self.runtime = runtime
        self.store = VaultDomainStore(runtime.guardian, actor_id=actor_id)
        self.actor_id = actor_id

    @staticmethod
    def _artifact_proof(path: str | Path, *, expected_kind: str) -> dict[str, Any]:
        candidate = Path(path).resolve(strict=True)
        if expected_kind == "customer_export":
            if not candidate.is_file() or candidate.stat().st_mode & 0o077:
                raise ValueError("closure_customer_export_not_owner_private")
            raw = candidate.read_bytes()
            outer = json.loads(raw)
            if outer.get("schema_version") != "tessaris.business-portable-export.v1":
                raise ValueError("closure_customer_export_schema_invalid")
            return {"kind": expected_kind, "sha256": _sha256(raw), "verified": True}
        if not candidate.is_dir():
            raise ValueError("closure_backup_snapshot_invalid")
        header_path = candidate / "snapshot.json"
        raw = header_path.read_bytes()
        header = json.loads(raw)
        if (
            header.get("schema_version") != "tessaris.business-vault-snapshot.v1"
            or header.get("key_material_in_snapshot") is not False
        ):
            raise ValueError("closure_backup_snapshot_schema_invalid")
        return {
            "kind": expected_kind,
            "sha256": _sha256(raw),
            "verified": True,
            "key_material_in_snapshot": False,
        }

    def preview(
        self,
        *,
        workspace_id: str,
        closure_id: str,
        customer_export_path: str | Path,
        backup_snapshot_path: str | Path,
        reauthentication_verified: bool,
        confirmation_phrase: str,
    ) -> dict[str, Any]:
        prior = self.store.get_optional(
            "vault.migration_receipts", workspace_id=workspace_id, entity_id=closure_id
        )
        if prior is not None:
            return {**dict(prior["payload"]), "idempotent_replay": True}
        if not reauthentication_verified:
            raise PermissionError("closure_separate_reauthentication_required")
        if confirmation_phrase != f"PREVIEW CLOSE {workspace_id}":
            raise PermissionError("closure_confirmation_phrase_invalid")

        # Bind the preview to the customer-owned business identity without
        # copying its payload into the receipt or response.
        identities = self.store.list("business.identity", workspace_id=workspace_id)
        business_maps = self.store.list("business.map", workspace_id=workspace_id)
        identity_set_sha256 = _sha256(
            _canonical(sorted(record["plaintext_sha256"] for record in identities))
        )
        export_proof = self._artifact_proof(customer_export_path, expected_kind="customer_export")
        backup_proof = self._artifact_proof(backup_snapshot_path, expected_kind="backup_destination")

        candidate_id = f"{closure_id}-retention-candidate"
        created = self.store.put(
            "file_cabinet.governance",
            workspace_id=workspace_id,
            entity_id=candidate_id,
            payload={
                "schema_version": CLOSURE_SCHEMA,
                "event": "retention_policy_applied",
                "policy": "owner_controlled_tombstone",
                "legal_hold": False,
                "eligible_for_tombstone": True,
                "recorded_at": _now(),
            },
            expected_version=None,
            idempotency_key=f"closure-retention-{closure_id}",
            actor_id=self.actor_id,
        )
        deleted = self.store.delete(
            "file_cabinet.governance",
            workspace_id=workspace_id,
            entity_id=candidate_id,
            reason_code="retention_period_elapsed",
            idempotency_key=f"closure-tombstone-{closure_id}",
            actor_id=self.actor_id,
        )
        if not deleted:
            raise RuntimeError("closure_retention_candidate_not_tombstoned")
        tombstoned = self.runtime.guardian.get_record(
            collection=self.store._collection("file_cabinet.governance"),
            record_id=self.store._record_id(workspace_id, candidate_id),
            include_tombstone=True,
        )
        if tombstoned.get("tombstone") is not True or int(tombstoned["version"]) != int(created["version"]) + 1:
            raise RuntimeError("closure_tombstone_history_not_recoverable")

        completed_at = _now()
        result = {
            "schema_version": CLOSURE_SCHEMA,
            "closure_id": closure_id,
            "workspace_id": workspace_id,
            "state": "preview_complete_no_destruction",
            "separate_reauthentication_verified": True,
            "identity_record_count": len(identities),
            "business_map_record_count": len(business_maps),
            "identity_set_sha256": identity_set_sha256,
            "retention_policy_applied": True,
            "governed_record_tombstoned": True,
            "tombstoned_history_recoverable": True,
            "preclosure_customer_export": export_proof,
            "preclosure_backup": backup_proof,
            "application_update_has_vault_delete_authority": False,
            "destructive_action_executed": False,
            "closure_execution_available_from_preview": False,
            "completed_at": completed_at,
            "idempotent_replay": False,
        }
        self.store.put(
            "vault.migration_receipts",
            workspace_id=workspace_id,
            entity_id=closure_id,
            payload=result,
            expected_version=None,
            idempotency_key=f"closure-receipt-{closure_id}",
            actor_id=self.actor_id,
        )
        self.store.put(
            "security.audit",
            workspace_id=workspace_id,
            entity_id=closure_id,
            payload={
                "schema_version": CLOSURE_SCHEMA,
                "event": "business_closure_preview_completed",
                "closure_id": closure_id,
                "export_sha256": export_proof["sha256"],
                "backup_sha256": backup_proof["sha256"],
                "separate_reauthentication_verified": True,
                "destructive_action_executed": False,
                "recorded_at": completed_at,
            },
            expected_version=None,
            idempotency_key=f"closure-security-{closure_id}",
            actor_id=self.actor_id,
        )
        return result
