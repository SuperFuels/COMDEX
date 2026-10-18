from __future__ import annotations

from hashlib import sha256
import json
import os
from typing import Any, Mapping

from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore


def _sortable_number(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


class AionLearningVaultStore:
    """Guardian-backed customer learning state and immutable learning evidence.

    This adapter is intentionally small.  AION's algorithms and public/base
    model assets remain application content; only learning derived from one
    business is stored here.  The business stable id is the default workspace
    boundary so a release cannot silently mingle two customers' learning.
    """

    STATE_DOMAIN = "learning.customer_state"
    AUDIT_DOMAIN = "learning.audit"

    def __init__(
        self,
        *,
        domain_store: VaultDomainStore | None = None,
        workspace_id: str | None = None,
        auto_configure: bool = True,
    ) -> None:
        self.domain_store = domain_store
        if domain_store is None and auto_configure and guardian_mode_requested():
            runtime = configured_business_vault_runtime()
            self.domain_store = VaultDomainStore(
                runtime.guardian,
                actor_id="aion-learning-runtime",
            )
        self.workspace_id = str(
            workspace_id
            or os.environ.get("TESSARIS_BUSINESS_STABLE_ID")
            or ""
        ).strip()
        if self.domain_store is not None and not self.workspace_id:
            raise ValueError("aion_learning_workspace_id_required")

    @property
    def enabled(self) -> bool:
        return self.domain_store is not None

    def put_state(self, entity_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if self.domain_store is None:
            raise RuntimeError("aion_learning_guardian_store_not_configured")
        current = self.domain_store.get_optional(
            self.STATE_DOMAIN,
            workspace_id=self.workspace_id,
            entity_id=entity_id,
        )
        canonical = json.dumps(
            dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode("utf-8")
        return self.domain_store.put(
            self.STATE_DOMAIN,
            workspace_id=self.workspace_id,
            entity_id=entity_id,
            payload=dict(payload),
            expected_version=int(current["version"]) if current else None,
            idempotency_key=f"learning-state-{sha256(canonical).hexdigest()[:32]}",
            actor_id="aion-learning-runtime",
        )

    def get_state(self, entity_id: str, default: Any) -> Any:
        if self.domain_store is None:
            return default
        row = self.domain_store.get_optional(
            self.STATE_DOMAIN,
            workspace_id=self.workspace_id,
            entity_id=entity_id,
        )
        return dict(row["payload"]) if row is not None else default

    def delete_state(self, entity_id: str) -> bool:
        if self.domain_store is None:
            return False
        return self.domain_store.delete(
            self.STATE_DOMAIN,
            workspace_id=self.workspace_id,
            entity_id=entity_id,
            reason_code="customer_learning_state_deleted",
            actor_id="aion-learning-runtime",
        )

    def append_event(self, entity_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if self.domain_store is None:
            raise RuntimeError("aion_learning_guardian_store_not_configured")
        if self.domain_store.get_optional(
            self.AUDIT_DOMAIN,
            workspace_id=self.workspace_id,
            entity_id=entity_id,
        ) is not None:
            raise ValueError("aion_learning_event_already_exists")
        return self.domain_store.put(
            self.AUDIT_DOMAIN,
            workspace_id=self.workspace_id,
            entity_id=entity_id,
            payload=dict(payload),
            expected_version=None,
            idempotency_key=(
                "learning-event-"
                + sha256(str(entity_id).encode("utf-8")).hexdigest()[:32]
            ),
            actor_id="aion-learning-runtime",
        )

    def list_events(self, *, kind: str | None = None) -> list[dict[str, Any]]:
        if self.domain_store is None:
            return []
        rows = self.domain_store.list(
            self.AUDIT_DOMAIN,
            workspace_id=self.workspace_id,
        )
        payloads = [dict(row["payload"]) for row in rows]
        if kind is not None:
            payloads = [row for row in payloads if row.get("event_type") == kind]
        return sorted(
            payloads,
            key=lambda row: (
                str(row.get("ts_utc") or ""),
                int(row.get("vault_order_ns") or 0),
                _sortable_number(row.get("timestamp")),
                str(row.get("event_id") or ""),
                str(row.get("audit_id") or ""),
            ),
        )
