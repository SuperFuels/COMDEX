"""Guardian-authoritative Boardroom seat conversation history."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.department_operational_store import (
    DepartmentOperationalStore,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore


_KEY = re.compile(r"[^a-z0-9_-]+")


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _key(value: str, fallback: str) -> str:
    result = _KEY.sub("-", str(value or "").strip().lower()).strip("-")
    return (result or fallback)[:80]


class BoardroomConversationService:
    """Persist customer Boardroom dialogue outside the replaceable application."""

    def __init__(self, *, domain_store: VaultDomainStore | None = None) -> None:
        self.domain_store = domain_store
        if domain_store is None and guardian_mode_requested():
            runtime = configured_business_vault_runtime()
            self.domain_store = VaultDomainStore(
                runtime.guardian, actor_id="boardroom-conversation-runtime"
            )

    def _store(self) -> VaultDomainStore:
        if self.domain_store is None:
            raise RuntimeError("business_vault_unavailable")
        return self.domain_store

    @staticmethod
    def _entity_id(team_mode: str, seat_key: str) -> str:
        return f"boardroom/conversations/{_key(team_mode, 'board')}/{_key(seat_key, 'aion')}"

    @staticmethod
    def _messages(values: list[Mapping[str, Any]]) -> list[dict[str, str]]:
        output: list[dict[str, str]] = []
        for value in values[-30:]:
            role = str(value.get("role") or "").strip().lower()
            text = str(value.get("text") or "").strip()
            if role not in {"user", "assistant"} or not text:
                continue
            output.append({
                "role": role,
                "text": text[:12000],
                "provider": str(value.get("provider") or "")[:120],
                "at": str(value.get("at") or _now())[:80],
            })
        return output

    def load(self, workspace_id: str, *, team_mode: str, seat_key: str) -> dict[str, Any]:
        workspace = canonical_business_id(workspace_id)
        entity_id = self._entity_id(team_mode, seat_key)
        row = self._store().get_optional(
            "departments.operational_records", workspace_id=workspace, entity_id=entity_id,
        )
        if row is None:
            return {
                "schema_version": "aion.boardroom.seat_conversation.v1",
                "workspace_id": workspace, "team_mode": _key(team_mode, "board"),
                "seat_key": _key(seat_key, "aion"), "messages": [], "revision": 0,
            }
        return {**dict(row["payload"]), "revision": int(row["version"])}

    def save(
        self, workspace_id: str, *, team_mode: str, seat_key: str,
        messages: list[Mapping[str, Any]], expected_revision: int | None = None,
    ) -> dict[str, Any]:
        workspace = canonical_business_id(workspace_id)
        entity_id = self._entity_id(team_mode, seat_key)
        current = self._store().get_optional(
            "departments.operational_records", workspace_id=workspace, entity_id=entity_id,
        )
        current_version = int(current["version"]) if current else None
        if expected_revision is not None and int(expected_revision) != int(current_version or 0):
            raise ValueError("boardroom_conversation_revision_conflict")
        normalized_messages = self._messages(messages)
        payload = {
            "schema_version": "aion.boardroom.seat_conversation.v1",
            "workspace_id": workspace,
            "team_mode": _key(team_mode, "board"),
            "seat_key": _key(seat_key, "aion"),
            "messages": normalized_messages,
            "updated_at": _now(),
        }
        stored = self._store().put(
            "departments.operational_records", workspace_id=workspace,
            entity_id=entity_id, payload=payload, expected_version=current_version,
        )
        revision = int(stored["version"])
        message_digest = sha256(
            json.dumps(
                normalized_messages,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        audit = DepartmentOperationalStore(
            domain_store=self._store()
        ).append_audit(
            workspace_id=workspace,
            department_id="boardroom",
            feature_id="seat_conversations",
            event_id=f"{_key(team_mode, 'board')}-{_key(seat_key, 'aion')}-revision-{revision}",
            payload={
                "schema_version": "aion.boardroom.conversation_revision_receipt.v1",
                "operation": "conversation_revision_committed",
                "team_mode": _key(team_mode, "board"),
                "seat_key": _key(seat_key, "aion"),
                "previous_revision": int(current_version or 0),
                "revision": revision,
                "message_count": len(normalized_messages),
                "content_digest": message_digest,
                "created_at": payload["updated_at"],
            },
            actor_id="boardroom-conversation-runtime",
        )
        return {
            **payload,
            "revision": revision,
            "audit_version": int(audit["version"]),
        }
