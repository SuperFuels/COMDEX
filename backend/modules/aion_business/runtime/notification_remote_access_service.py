"""Guardian-backed notification evidence and remote-access governance.

Notification content remains an authoritative Support record.  Provider receipts
and remote-access audit events are deliberately content-minimised.  Usable phone
authority is supplied by ``MobilePairingAuthority`` and never enters this store.
"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
import re
from typing import Any, Callable, Mapping

from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}$")


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _identifier(value: str, label: str) -> str:
    clean = str(value or "").strip()
    if not _IDENTIFIER.fullmatch(clean):
        raise ValueError(f"notification_remote_access_{label}_invalid")
    return clean


def _digest(value: Any) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str,
    ).encode("utf-8")
    return "sha256:" + sha256(raw).hexdigest()


class NotificationRemoteAccessService:
    """Own notification records and public remote-session lifecycle evidence."""

    def __init__(self, *, domain_store: VaultDomainStore | None = None) -> None:
        self.domain_store = domain_store
        if domain_store is None and guardian_mode_requested():
            runtime = configured_business_vault_runtime()
            self.domain_store = VaultDomainStore(
                runtime.guardian, actor_id="notification-remote-access-runtime",
            )

    def _required_store(self) -> VaultDomainStore:
        if self.domain_store is None:
            raise RuntimeError("notification_remote_access_guardian_store_required")
        return self.domain_store

    def prepare_notification(
        self,
        workspace_id: str,
        *,
        notification_id: str,
        recipient: str,
        channel: str,
        content: str,
        actor_id: str,
    ) -> dict[str, Any]:
        store = self._required_store()
        workspace_id = canonical_business_id(workspace_id)
        notification_id = _identifier(notification_id, "notification_id")
        clean_channel = str(channel or "").strip().lower()
        if clean_channel not in {"email", "sms", "push"}:
            raise ValueError("notification_remote_access_channel_invalid")
        clean_recipient = str(recipient or "").strip()[:320]
        clean_content = str(content or "").strip()
        if not clean_recipient or not clean_content or len(clean_content.encode("utf-8")) > 64_000:
            raise ValueError("notification_remote_access_content_invalid")
        entity_id = f"notifications/{notification_id}"
        existing = store.get_optional(
            "support.records", workspace_id=workspace_id, entity_id=entity_id,
        )
        content_digest = _digest({"recipient": clean_recipient, "content": clean_content})
        if existing is not None:
            payload = dict(existing["payload"])
            if payload.get("content_digest") != content_digest or payload.get("channel") != clean_channel:
                raise ValueError("notification_prepare_idempotency_conflict")
            return {"notification": payload, "idempotent_replay": True}
        created_at = _now()
        payload = {
            "schema_version": "tessaris.notification-record.v1",
            "notification_id": notification_id,
            "channel": clean_channel,
            "recipient": clean_recipient,
            "content": clean_content,
            "content_digest": content_digest,
            "status": "prepared",
            "attempt_count": 0,
            "prepared_at": created_at,
            "prepared_by": str(actor_id or "business-operator")[:160],
            "provider": None,
            "provider_receipt_hash": None,
            "delivered_at": None,
        }
        store.put(
            "support.records", workspace_id=workspace_id, entity_id=entity_id,
            payload=payload, expected_version=None,
            idempotency_key=f"notification-prepare-{sha256(notification_id.encode()).hexdigest()}",
            actor_id="notification-remote-access-runtime",
        )
        self._operational_receipt(
            workspace_id, event_id=f"notification-{notification_id}-prepared",
            event_type="notification_prepared", subject_id=notification_id,
            subject_digest=content_digest, actor_id=actor_id,
        )
        return {"notification": payload, "idempotent_replay": False}

    def deliver_notification(
        self,
        workspace_id: str,
        *,
        notification_id: str,
        actor_id: str,
        sender: Callable[[dict[str, Any]], Mapping[str, Any]],
    ) -> dict[str, Any]:
        store = self._required_store()
        workspace_id = canonical_business_id(workspace_id)
        notification_id = _identifier(notification_id, "notification_id")
        entity_id = f"notifications/{notification_id}"
        current = store.get_optional(
            "support.records", workspace_id=workspace_id, entity_id=entity_id,
        )
        if current is None:
            raise LookupError("notification_not_found")
        payload = dict(current["payload"])
        if payload.get("status") == "delivered":
            return {
                "notification": self.public_notification(payload),
                "idempotent_replay": True,
                "external_delivery_performed": False,
            }
        receipt = dict(sender({
            "notification_id": notification_id,
            "channel": payload["channel"],
            "recipient": payload["recipient"],
            "content": payload["content"],
            "content_digest": payload["content_digest"],
        }))
        provider = str(receipt.get("provider") or "")[:120]
        provider_request_id = str(receipt.get("provider_request_id") or "")
        accepted = bool(receipt.get("ok")) and bool(provider) and bool(provider_request_id)
        payload["attempt_count"] = int(payload.get("attempt_count") or 0) + 1
        payload["provider"] = provider or None
        payload["last_attempt_at"] = _now()
        payload["last_attempt_by"] = str(actor_id or "business-operator")[:160]
        if accepted:
            payload["status"] = "delivered"
            payload["delivered_at"] = payload["last_attempt_at"]
            payload["provider_receipt_hash"] = _digest({
                "provider": provider,
                "provider_request_id": provider_request_id,
                "provider_status": str(receipt.get("provider_status") or "accepted"),
            })
            payload["failure_code"] = None
        else:
            payload["status"] = "delivery_failed"
            payload["provider_receipt_hash"] = None
            payload["failure_code"] = str(receipt.get("error_code") or "provider_receipt_missing")[:160]
        store.put(
            "support.records", workspace_id=workspace_id, entity_id=entity_id,
            payload=payload, expected_version=int(current["version"]),
            idempotency_key=f"notification-attempt-{notification_id}-{payload['attempt_count']}",
            actor_id="notification-remote-access-runtime",
        )
        self._operational_receipt(
            workspace_id,
            event_id=f"notification-{notification_id}-attempt-{payload['attempt_count']}",
            event_type="notification_delivered" if accepted else "notification_delivery_failed",
            subject_id=notification_id,
            subject_digest=str(payload["content_digest"]), actor_id=actor_id,
            details={
                "attempt": payload["attempt_count"], "provider": provider or "unknown",
                "provider_receipt_hash": payload.get("provider_receipt_hash"),
            },
        )
        return {
            "notification": self.public_notification(payload),
            "idempotent_replay": False,
            "external_delivery_performed": accepted,
        }

    @staticmethod
    def public_notification(payload: Mapping[str, Any]) -> dict[str, Any]:
        """Return delivery evidence without copying content or recipient to logs/UI."""
        return {
            key: payload.get(key)
            for key in (
                "schema_version", "notification_id", "channel", "content_digest", "status",
                "attempt_count", "provider", "provider_receipt_hash", "prepared_at",
                "delivered_at", "failure_code",
            )
        }

    def notification_status(self, workspace_id: str, notification_id: str) -> dict[str, Any]:
        store = self._required_store()
        workspace_id = canonical_business_id(workspace_id)
        notification_id = _identifier(notification_id, "notification_id")
        result = store.get_optional(
            "support.records", workspace_id=workspace_id,
            entity_id=f"notifications/{notification_id}",
        )
        if result is None:
            raise LookupError("notification_not_found")
        return self.public_notification(result["payload"])

    def record_remote_opened(
        self,
        workspace_id: str,
        *,
        session_id: str,
        device_id: str,
        persona_id: str,
        scopes: list[str],
        certificate_fingerprint: str,
        actor_id: str,
    ) -> dict[str, Any]:
        workspace_id = canonical_business_id(workspace_id)
        session_id = _identifier(session_id, "session_id")
        device_id = _identifier(device_id, "device_id")
        now = _now()
        payload = {
            "schema_version": "tessaris.remote-access-session.v1",
            "session_id": session_id,
            "device_id": device_id,
            "persona_id": str(persona_id or "")[:160],
            "scopes": sorted(set(str(scope) for scope in scopes if str(scope))),
            "certificate_fingerprint": str(certificate_fingerprint or "")[:160],
            "status": "connected",
            "opened_at": now,
            "opened_by": str(actor_id or "business-operator")[:160],
            "revoked_at": None,
            "authority_stored_in_vault": False,
        }
        self._put_security_session(workspace_id, session_id, payload)
        self._security_receipt(
            workspace_id, session_id=session_id, event_type="remote_access_opened",
            device_id=device_id, actor_id=actor_id,
        )
        return payload

    def record_remote_revoked(
        self,
        workspace_id: str,
        *,
        session_id: str,
        revocation: Mapping[str, Any],
        actor_id: str,
    ) -> dict[str, Any]:
        store = self._required_store()
        workspace_id = canonical_business_id(workspace_id)
        session_id = _identifier(session_id, "session_id")
        entity_id = f"remote_access/sessions/{session_id}"
        current = store.get_optional(
            "security.records", workspace_id=workspace_id, entity_id=entity_id,
        )
        if current is None:
            raise LookupError("remote_access_session_not_found")
        payload = dict(current["payload"])
        if payload.get("status") == "revoked":
            return {**payload, "idempotent_replay": True}
        if str(revocation.get("status") or "") != "revoked":
            raise ValueError("remote_access_revocation_not_confirmed")
        payload.update({
            "status": "revoked", "revoked_at": _now(),
            "revoked_by": str(actor_id or "business-operator")[:160],
            "leases_revoked": int(revocation.get("leases_revoked") or 0),
        })
        store.put(
            "security.records", workspace_id=workspace_id, entity_id=entity_id,
            payload=payload, expected_version=int(current["version"]),
            actor_id="notification-remote-access-runtime",
        )
        self._security_receipt(
            workspace_id, session_id=session_id, event_type="remote_access_revoked",
            device_id=str(payload["device_id"]), actor_id=actor_id,
        )
        return {**payload, "idempotent_replay": False}

    def remote_status(self, workspace_id: str, session_id: str) -> dict[str, Any]:
        store = self._required_store()
        workspace_id = canonical_business_id(workspace_id)
        session_id = _identifier(session_id, "session_id")
        result = store.get_optional(
            "security.records", workspace_id=workspace_id,
            entity_id=f"remote_access/sessions/{session_id}",
        )
        if result is None:
            raise LookupError("remote_access_session_not_found")
        return dict(result["payload"])

    def _put_security_session(self, workspace_id: str, session_id: str, payload: dict[str, Any]) -> None:
        store = self._required_store()
        entity_id = f"remote_access/sessions/{session_id}"
        current = store.get_optional(
            "security.records", workspace_id=workspace_id, entity_id=entity_id,
        )
        store.put(
            "security.records", workspace_id=workspace_id, entity_id=entity_id,
            payload=payload, expected_version=int(current["version"]) if current else None,
            actor_id="notification-remote-access-runtime",
        )

    def _operational_receipt(
        self, workspace_id: str, *, event_id: str, event_type: str, subject_id: str,
        subject_digest: str, actor_id: str, details: Mapping[str, Any] | None = None,
    ) -> None:
        store = self._required_store()
        receipt = {
            "schema_version": "tessaris.notification-delivery-receipt.v1",
            "event_id": event_id, "event_type": event_type,
            "notification_id": subject_id, "content_digest": subject_digest,
            "occurred_at": _now(), "actor_id": str(actor_id or "business-operator")[:160],
            "contains_content": False, "contains_recipient": False,
            **dict(details or {}),
        }
        store.put(
            "departments.operational_audit", workspace_id=workspace_id,
            entity_id=f"notifications/receipts/{event_id}", payload=receipt,
            expected_version=None,
            idempotency_key=f"notification-receipt-{sha256(event_id.encode()).hexdigest()}",
            actor_id="notification-remote-access-runtime",
        )

    def _security_receipt(
        self, workspace_id: str, *, session_id: str, event_type: str,
        device_id: str, actor_id: str,
    ) -> None:
        store = self._required_store()
        receipt_id = f"{session_id}-{event_type}"
        receipt = {
            "schema_version": "tessaris.remote-access-receipt.v1",
            "event_type": event_type, "session_id": session_id,
            "device_id_hash": _digest(device_id), "occurred_at": _now(),
            "actor_id": str(actor_id or "business-operator")[:160],
            "contains_authority": False,
        }
        store.put(
            "security.audit", workspace_id=workspace_id,
            entity_id=f"remote_access/receipts/{receipt_id}", payload=receipt,
            expected_version=None,
            idempotency_key=f"remote-access-receipt-{sha256(receipt_id.encode()).hexdigest()}",
            actor_id="notification-remote-access-runtime",
        )
