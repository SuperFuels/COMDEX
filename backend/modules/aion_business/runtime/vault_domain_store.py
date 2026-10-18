from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
import sys
from typing import Any, Mapping
from uuid import uuid4

from backend.modules.aion_business.runtime.business_data_domain_registry import (
    BusinessDataDomainRegistry,
)
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _identity_hash(workspace_id: str, entity_id: str) -> str:
    raw = f"{workspace_id}\0{entity_id}".encode("utf-8")
    return sha256(raw).hexdigest()


class VaultDomainStore:
    """Encrypted JSON store for registered business-data domains."""

    def __init__(
        self,
        guardian: VaultGuardian,
        *,
        registry: BusinessDataDomainRegistry | None = None,
        actor_id: str = "business-runtime",
    ) -> None:
        self.guardian = guardian
        self.registry = registry or BusinessDataDomainRegistry()
        self.actor_id = actor_id

    def _collection(self, domain_id: str) -> str:
        return self.registry.get(domain_id).guardian_collection

    @staticmethod
    def _audit_domain_access(domain_id: str, operation: str) -> None:
        # Discovery records only the registered domain identifier and operation.
        # Payloads, workspace identifiers and entity identifiers never enter the
        # process-wide audit event.
        sys.audit("tessaris.vault_domain_access", domain_id, operation)

    @staticmethod
    def _record_id(workspace_id: str, entity_id: str) -> str:
        return f"d-{_identity_hash(workspace_id, entity_id)}"

    def put(
        self,
        domain_id: str,
        *,
        workspace_id: str,
        entity_id: str,
        payload: Mapping[str, Any],
        expected_version: int | None = None,
        idempotency_key: str | None = None,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        self._audit_domain_access(domain_id, "put")
        collection = self._collection(domain_id)
        body = {
            "schema_version": "tessaris.vault-domain-record.v1",
            "domain_id": domain_id,
            "workspace_id": str(workspace_id),
            "entity_id": str(entity_id),
            "payload": dict(payload),
        }
        return self.guardian.put_record(
            collection=collection,
            record_id=self._record_id(workspace_id, entity_id),
            payload=body,
            expected_version=expected_version,
            idempotency_key=idempotency_key or f"domain-{uuid4().hex}",
            actor_id=actor_id or self.actor_id,
            recorded_at=_now(),
        )

    def get(self, domain_id: str, *, workspace_id: str, entity_id: str) -> dict[str, Any]:
        self._audit_domain_access(domain_id, "get")
        record = self.guardian.get_record(
            collection=self._collection(domain_id),
            record_id=self._record_id(workspace_id, entity_id),
        )
        envelope = record["payload"]
        if (
            envelope.get("domain_id") != domain_id
            or envelope.get("workspace_id") != str(workspace_id)
            or envelope.get("entity_id") != str(entity_id)
        ):
            raise RuntimeError("vault_domain_record_identity_mismatch")
        return {**record, "payload": dict(envelope["payload"])}

    def get_optional(
        self, domain_id: str, *, workspace_id: str, entity_id: str
    ) -> dict[str, Any] | None:
        try:
            return self.get(domain_id, workspace_id=workspace_id, entity_id=entity_id)
        except KeyError:
            return None

    def list(self, domain_id: str, *, workspace_id: str) -> list[dict[str, Any]]:
        self._audit_domain_access(domain_id, "list")
        records = self.guardian.list_records(collection=self._collection(domain_id))
        output: list[dict[str, Any]] = []
        for record in records:
            envelope = record["payload"]
            if envelope.get("domain_id") != domain_id or envelope.get("workspace_id") != str(workspace_id):
                continue
            output.append({**record, "payload": dict(envelope["payload"]), "entity_id": envelope["entity_id"]})
        return output

    def list_all(self, domain_id: str) -> list[dict[str, Any]]:
        """List a domain across workspaces without creating a filesystem index."""
        self._audit_domain_access(domain_id, "list_all")
        records = self.guardian.list_records(collection=self._collection(domain_id))
        output: list[dict[str, Any]] = []
        for record in records:
            envelope = record["payload"]
            if envelope.get("domain_id") != domain_id:
                continue
            output.append(
                {
                    **record,
                    "payload": dict(envelope["payload"]),
                    "workspace_id": envelope["workspace_id"],
                    "entity_id": envelope["entity_id"],
                }
            )
        return output

    def delete(
        self,
        domain_id: str,
        *,
        workspace_id: str,
        entity_id: str,
        reason_code: str = "customer_record_deleted",
        idempotency_key: str | None = None,
        actor_id: str | None = None,
    ) -> bool:
        """Tombstone one domain record while preserving Guardian audit history."""

        existing = self.get_optional(
            domain_id,
            workspace_id=workspace_id,
            entity_id=entity_id,
        )
        if existing is None:
            return False
        self._audit_domain_access(domain_id, "delete")
        self.guardian.tombstone_record(
            collection=self._collection(domain_id),
            record_id=self._record_id(workspace_id, entity_id),
            expected_version=int(existing["version"]),
            reason_code=reason_code,
            idempotency_key=idempotency_key or f"domain-delete-{uuid4().hex}",
            actor_id=actor_id or self.actor_id,
            recorded_at=_now(),
        )
        return True
