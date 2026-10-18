from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore


class DepartmentOperationalStore:
    """Vault store for records introduced by present and future departments.

    The department and feature prefixes keep independently shipped features
    isolated while the registered wildcard domain ensures that a newly added
    department cannot silently invent an application-local data directory.
    """

    DOMAIN_ID = "departments.operational_records"
    AUDIT_DOMAIN_ID = "departments.operational_audit"

    def __init__(self, *, domain_store: VaultDomainStore | None = None) -> None:
        self.domain_store = domain_store
        if domain_store is None and guardian_mode_requested():
            runtime = configured_business_vault_runtime()
            self.domain_store = VaultDomainStore(
                runtime.guardian, actor_id="department-operational-runtime",
            )

    @staticmethod
    def entity_id(department_id: str, feature_id: str, record_id: str) -> str:
        parts = []
        for label, value in (
            ("department_id", department_id),
            ("feature_id", feature_id),
            ("record_id", record_id),
        ):
            normalized = str(value or "").strip().strip("/")
            if not normalized or normalized in {".", ".."} or "//" in normalized:
                raise ValueError(f"department_operational_{label}_invalid")
            parts.append(normalized)
        return "/".join(parts)

    def put(
        self,
        *,
        workspace_id: str,
        department_id: str,
        feature_id: str,
        record_id: str,
        payload: Mapping[str, Any],
        actor_id: str = "department-operational-runtime",
    ) -> dict[str, Any]:
        if self.domain_store is None:
            raise RuntimeError("department_operational_guardian_store_not_configured")
        entity_id = self.entity_id(department_id, feature_id, record_id)
        current = self.domain_store.get_optional(
            self.DOMAIN_ID, workspace_id=workspace_id, entity_id=entity_id,
        )
        canonical = json.dumps(
            dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode("utf-8")
        return self.domain_store.put(
            self.DOMAIN_ID,
            workspace_id=workspace_id,
            entity_id=entity_id,
            payload=dict(payload),
            expected_version=int(current["version"]) if current else None,
            idempotency_key=f"department-operational-{sha256(canonical).hexdigest()[:32]}",
            actor_id=actor_id,
        )

    def get_optional(
        self,
        *,
        workspace_id: str,
        department_id: str,
        feature_id: str,
        record_id: str,
    ) -> dict[str, Any] | None:
        if self.domain_store is None:
            return None
        return self.domain_store.get_optional(
            self.DOMAIN_ID,
            workspace_id=workspace_id,
            entity_id=self.entity_id(department_id, feature_id, record_id),
        )

    def list_feature(
        self, *, workspace_id: str, department_id: str, feature_id: str,
    ) -> list[dict[str, Any]]:
        if self.domain_store is None:
            return []
        prefix = self.entity_id(department_id, feature_id, "record-placeholder").rsplit("/", 1)[0] + "/"
        return [
            row
            for row in self.domain_store.list(self.DOMAIN_ID, workspace_id=workspace_id)
            if str(row.get("entity_id") or "").startswith(prefix)
        ]

    def append_audit(
        self,
        *,
        workspace_id: str,
        department_id: str,
        feature_id: str,
        event_id: str,
        payload: Mapping[str, Any],
        actor_id: str = "department-operational-runtime",
    ) -> dict[str, Any]:
        if self.domain_store is None:
            raise RuntimeError("department_operational_guardian_store_not_configured")
        entity_id = self.entity_id(department_id, feature_id, event_id)
        if self.domain_store.get_optional(
            self.AUDIT_DOMAIN_ID, workspace_id=workspace_id, entity_id=entity_id,
        ) is not None:
            raise ValueError("department_operational_audit_event_already_exists")
        return self.domain_store.put(
            self.AUDIT_DOMAIN_ID,
            workspace_id=workspace_id,
            entity_id=entity_id,
            payload=dict(payload),
            expected_version=None,
            idempotency_key=(
                "department-operational-audit-"
                + sha256(str(event_id).encode("utf-8")).hexdigest()[:32]
            ),
            actor_id=actor_id,
        )

    def list_audit(
        self, *, workspace_id: str, department_id: str, feature_id: str,
    ) -> list[dict[str, Any]]:
        if self.domain_store is None:
            return []
        prefix = self.entity_id(department_id, feature_id, "event-placeholder").rsplit("/", 1)[0] + "/"
        rows = [
            row
            for row in self.domain_store.list(self.AUDIT_DOMAIN_ID, workspace_id=workspace_id)
            if str(row.get("entity_id") or "").startswith(prefix)
        ]
        return sorted(
            rows,
            key=lambda row: (
                str((row.get("payload") or {}).get("created_at") or (row.get("payload") or {}).get("at") or ""),
                str(row.get("entity_id") or ""),
            ),
        )


class BusinessOperationsRecordRepository:
    """Small typed-repository adapter over the generic department domain."""

    DEPARTMENT_ID = "business_operations"

    def __init__(
        self, feature_id: str, *, operational_store: DepartmentOperationalStore | None = None,
    ) -> None:
        self.feature_id = str(feature_id).strip()
        self.operational_store = operational_store or DepartmentOperationalStore()

    @property
    def enabled(self) -> bool:
        return self.operational_store.domain_store is not None

    def put(self, workspace_id: str, record_id: str, payload: Mapping[str, Any], *, actor_id: str) -> None:
        self.operational_store.put(
            workspace_id=workspace_id, department_id=self.DEPARTMENT_ID,
            feature_id=self.feature_id, record_id=record_id, payload=payload,
            actor_id=actor_id,
        )

    def get_optional(self, workspace_id: str, record_id: str) -> dict[str, Any] | None:
        record = self.operational_store.get_optional(
            workspace_id=workspace_id, department_id=self.DEPARTMENT_ID,
            feature_id=self.feature_id, record_id=record_id,
        )
        if record is None or bool((record.get("payload") or {}).get("__deleted__")):
            return None
        return record

    def list_workspace(self, workspace_id: str) -> list[dict[str, Any]]:
        return [
            row for row in self.operational_store.list_feature(
                workspace_id=workspace_id, department_id=self.DEPARTMENT_ID,
                feature_id=self.feature_id,
            )
            if not bool((row.get("payload") or {}).get("__deleted__"))
        ]

    def list_all(self) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        prefix = f"{self.DEPARTMENT_ID}/{self.feature_id}/"
        return [
            row for row in self.operational_store.domain_store.list_all(
                DepartmentOperationalStore.DOMAIN_ID,
            )
            if str(row.get("entity_id") or "").startswith(prefix)
            and not bool((row.get("payload") or {}).get("__deleted__"))
        ]

    def delete(self, workspace_id: str, record_id: str, *, actor_id: str) -> bool:
        if self.get_optional(workspace_id, record_id) is None:
            return False
        self.put(
            workspace_id, record_id,
            {"__deleted__": True, "workspace_id": workspace_id, "record_id": record_id},
            actor_id=actor_id,
        )
        return True
