from __future__ import annotations

from typing import Any, Mapping
from uuid import uuid4

from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore


AUTOMATION_DOMAIN = "train_agent.automations"
AUDIT_DOMAIN = "train_agent.runs_and_audit"


def configured_agent_domain_store() -> VaultDomainStore | None:
    """Return the encrypted Train Agent store when Guardian mode is enabled.

    A requested but incomplete Guardian configuration deliberately raises from
    ``configured_business_vault_runtime`` instead of falling back to plaintext.
    """

    if not guardian_mode_requested():
        return None
    return VaultDomainStore(
        configured_business_vault_runtime().guardian,
        actor_id="aion-agent-runtime",
    )


class AgentVaultRepositoryBackend:
    """Small compatibility adapter for legacy AION Agent repositories."""

    def __init__(
        self,
        store: VaultDomainStore,
        *,
        kind: str,
        audit: bool = False,
    ) -> None:
        self.store = store
        self.kind = str(kind).strip("/")
        self.domain_id = AUDIT_DOMAIN if audit else AUTOMATION_DOMAIN

    def _entity_id(self, item_id: str) -> str:
        return f"legacy_aion_agents/{self.kind}/{item_id}"

    def put(
        self,
        *,
        workspace_id: str,
        item_id: str,
        payload: Mapping[str, Any],
    ) -> None:
        entity_id = self._entity_id(item_id)
        existing = self.store.get_optional(
            self.domain_id,
            workspace_id=workspace_id,
            entity_id=entity_id,
        )
        self.store.put(
            self.domain_id,
            workspace_id=workspace_id,
            entity_id=entity_id,
            payload=payload,
            expected_version=int(existing["version"]) if existing else None,
            idempotency_key=f"aion-agent-{uuid4().hex}",
            actor_id="aion-agent-runtime",
        )

    def get(self, *, workspace_id: str, item_id: str) -> dict[str, Any] | None:
        record = self.store.get_optional(
            self.domain_id,
            workspace_id=workspace_id,
            entity_id=self._entity_id(item_id),
        )
        return dict(record["payload"]) if record else None

    def exists(self, *, workspace_id: str, item_id: str) -> bool:
        return self.get(workspace_id=workspace_id, item_id=item_id) is not None

    def delete(self, *, workspace_id: str, item_id: str) -> bool:
        return self.store.delete(
            self.domain_id,
            workspace_id=workspace_id,
            entity_id=self._entity_id(item_id),
            reason_code="aion_agent_record_deleted",
            actor_id="aion-agent-runtime",
        )

    def list(self, *, workspace_id: str) -> list[dict[str, Any]]:
        prefix = f"legacy_aion_agents/{self.kind}/"
        return [
            dict(record["payload"])
            for record in self.store.list(self.domain_id, workspace_id=workspace_id)
            if str(record.get("entity_id") or "").startswith(prefix)
        ]
