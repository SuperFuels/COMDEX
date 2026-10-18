"""Encrypted, approval-gated delivery outbox for completed Legal evidence."""

from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import threading
from typing import Any, Callable, Mapping
from uuid import uuid4

from backend.modules.aion_business.runtime.legal_secure_storage import LegalEncryptedStore, LegalKeyStore
from backend.modules.aion_business.runtime.legal_resource_limits import (
    bounded_record_paths,
    ensure_workspace_record_write,
    estimated_encrypted_record_bytes,
)


class LegalDeliveryError(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class LegalDeliveryService:
    """Persist the exact approved message and attachment before any provider call."""

    SCHEMA_VERSION = "tessaris.legal-delivery-outbox.v1"
    PROVIDERS = {"microsoft_graph", "resend"}
    FINAL = {"DELIVERED", "BOUNCED", "REJECTED"}
    RESEND_EVENT_TYPES = {
        "email.sent", "email.delivered", "email.delivery_delayed",
        "email.bounced", "email.failed", "email.suppressed", "email.complained",
    }
    MAX_ATTACHMENT_BYTES = 50 * 1024 * 1024
    MAX_EVENTS = 2_000

    def __init__(
        self,
        root: str | Path,
        *,
        clock: Callable[[], datetime] = _now,
        key_store: LegalKeyStore | None = None,
        senders: Mapping[str, Callable[[Mapping[str, Any]], Mapping[str, Any]]] | None = None,
        receipt_checkers: Mapping[str, Callable[[Mapping[str, Any]], Mapping[str, Any]]] | None = None,
    ) -> None:
        self.base_root = Path(root)
        self.root = self.base_root / "_delivery_outbox"
        self.clock = clock
        self.keys = key_store or LegalKeyStore(Path(root))
        self.store = LegalEncryptedStore(
            Path(root), purpose="legal_delivery_outbox", key_store=self.keys,
        )
        self.index_store = LegalEncryptedStore(
            Path(root), purpose="legal_delivery_provider_index", key_store=self.keys,
        )
        self.senders = dict(senders or {})
        self.receipt_checkers = dict(receipt_checkers or {})
        self._lock = threading.RLock()

    def queue(
        self,
        workspace_id: str,
        *,
        envelope_id: str,
        manifest_hash: str,
        signer: Mapping[str, Any],
        provider: str,
        subject: str,
        body_text: str,
        attachment_name: str,
        attachment_bytes: bytes,
        approved_by: str,
        acknowledge_external_send: bool,
    ) -> dict[str, Any]:
        provider = str(provider or "").strip().lower()
        if provider not in self.PROVIDERS:
            raise LegalDeliveryError("unsupported_legal_delivery_provider")
        if not acknowledge_external_send:
            raise LegalDeliveryError("external_send_acknowledgement_required")
        recipient = str(signer.get("email") or "").strip().lower()
        signer_id = str(signer.get("signer_id") or "").strip()
        if not signer_id or "@" not in recipient:
            raise LegalDeliveryError("valid_signer_delivery_recipient_required")
        if not attachment_bytes:
            raise LegalDeliveryError("signed_evidence_attachment_required")
        if len(attachment_bytes) > self.MAX_ATTACHMENT_BYTES:
            raise LegalDeliveryError("signed_evidence_attachment_too_large")
        attachment_hash = sha256(attachment_bytes).hexdigest()
        identity = {
            "workspace_id": workspace_id,
            "envelope_id": envelope_id,
            "manifest_hash": manifest_hash,
            "signer_id": signer_id,
            "recipient": recipient,
            "provider": provider,
        }
        delivery_id = f"delivery-{sha256(_canonical(identity)).hexdigest()[:32]}"
        path = self._path(workspace_id, delivery_id)
        with self._lock:
            if path.exists():
                current = self._read(path, workspace_id, delivery_id)
                if not hmac.compare_digest(str(current.get("immutable_payload_sha256") or ""), sha256(_canonical(identity)).hexdigest()):
                    raise LegalDeliveryError("delivery_idempotency_conflict")
                return self._public(current)
            now = _iso(self.clock())
            record: dict[str, Any] = {
                "schema_version": self.SCHEMA_VERSION,
                "delivery_id": delivery_id,
                **identity,
                "attachment_sha256": attachment_hash,
                "immutable_payload_sha256": sha256(_canonical(identity)).hexdigest(),
                "status": "APPROVED_PENDING",
                "approved_at": now,
                "approved_by": str(approved_by or "unknown")[:160],
                "attempt_count": 0,
                "next_attempt_at": now,
                "last_error": None,
                "provider_request_id": None,
                "provider_status": None,
                "submitted_at": None,
                "confirmed_at": None,
                "confirmation_reference": None,
                "provider_events": [],
                "provider_outcome_conflict": None,
                "message": {"subject": str(subject)[:300], "body_text": str(body_text)[:20_000]},
                "attachment": {
                    "filename": str(attachment_name)[:240],
                    "content_type": "application/zip",
                    "sha256": attachment_hash,
                    "content_base64": base64.b64encode(attachment_bytes).decode("ascii"),
                },
                "events": [],
            }
            self._event(record, "DELIVERY_APPROVED_AND_QUEUED", approved_by, {"provider": provider})
            self._save(record)
            return self._public(record)

    def status(self, workspace_id: str, envelope_id: str | None = None) -> dict[str, Any]:
        records = self._records(workspace_id)
        if envelope_id:
            records = [item for item in records if item.get("envelope_id") == envelope_id]
        counts: dict[str, int] = {}
        for item in records:
            status = str(item.get("status") or "UNKNOWN")
            counts[status] = counts.get(status, 0) + 1
        required = len(records)
        confirmed = sum(item.get("status") == "DELIVERED" for item in records)
        return {
            "counts": counts,
            "items": [self._public(item) for item in records],
            "required_party_count": required,
            "confirmed_party_count": confirmed,
            "all_required_parties_confirmed": bool(required) and confirmed == required,
            "event_chains_valid": all(self.verify_event_chain(item) for item in records),
        }

    @staticmethod
    def verify_event_chain(record: Mapping[str, Any]) -> bool:
        previous = "GENESIS"
        for event in record.get("events") or []:
            if event.get("previous_hash") != previous:
                return False
            body = {key: value for key, value in event.items() if key != "event_hash"}
            expected = sha256(_canonical(body)).hexdigest()
            if not hmac.compare_digest(str(event.get("event_hash") or ""), expected):
                return False
            previous = expected
        return True

    def deliver_due(
        self,
        workspace_id: str,
        *,
        actor_id: str,
        acknowledge_external_send: bool,
        limit: int = 25,
        force: bool = False,
    ) -> dict[str, Any]:
        if not acknowledge_external_send:
            raise LegalDeliveryError("external_send_acknowledgement_required")
        attempted: list[dict[str, Any]] = []
        for item in self._records(workspace_id):
            if len(attempted) >= max(1, min(int(limit), 250)):
                break
            if item.get("status") not in {"APPROVED_PENDING", "RETRY_PENDING"}:
                continue
            due = datetime.fromisoformat(str(item["next_attempt_at"]).replace("Z", "+00:00"))
            if not force and due > self.clock():
                continue
            attempted.append(self._deliver(item, actor_id))
        result = self.status(workspace_id)
        return {**result, "attempted": attempted, "attempted_count": len(attempted)}

    def confirm(
        self,
        workspace_id: str,
        delivery_id: str,
        *,
        outcome: str,
        provider_reference: str,
        actor_id: str,
    ) -> dict[str, Any]:
        outcome = str(outcome or "").strip().upper()
        if outcome not in {"DELIVERED", "BOUNCED", "REJECTED"}:
            raise LegalDeliveryError("unsupported_delivery_confirmation_outcome")
        reference = " ".join(str(provider_reference or "").split()).strip()[:500]
        if not reference:
            raise LegalDeliveryError("provider_confirmation_reference_required")
        with self._lock:
            record = self._load(workspace_id, delivery_id)
            if record.get("status") not in {"SUBMITTED_TO_PROVIDER", "DELIVERED", "BOUNCED", "REJECTED"}:
                raise LegalDeliveryError("delivery_must_be_submitted_before_confirmation")
            if record.get("status") in self.FINAL:
                if record["status"] != outcome or record.get("confirmation_reference") != reference:
                    raise LegalDeliveryError("delivery_confirmation_conflict")
                return self._public(record)
            record.update({
                "status": outcome,
                "confirmed_at": _iso(self.clock()),
                "confirmation_reference": reference,
            })
            self._event(record, f"DELIVERY_{outcome}", actor_id, {"provider_reference": reference})
            self._save(record)
            return self._public(record)

    def retry_or_resend(
        self,
        workspace_id: str,
        delivery_id: str,
        *,
        actor_id: str,
        reason: str,
        acknowledge_external_send: bool,
    ) -> dict[str, Any]:
        if not acknowledge_external_send:
            raise LegalDeliveryError("external_send_acknowledgement_required")
        reason = " ".join(str(reason or "").split()).strip()[:500]
        if not reason:
            raise LegalDeliveryError("delivery_retry_reason_required")
        with self._lock:
            record = self._load(workspace_id, delivery_id)
            if record.get("status") not in {"SUBMITTED_TO_PROVIDER", "DELIVERY_DELAYED", "RETRY_PENDING", "BOUNCED", "REJECTED"}:
                raise LegalDeliveryError("delivery_not_eligible_for_retry")
            history = record.setdefault("provider_history", [])
            history.append({
                "status": record.get("status"),
                "provider_request_id": record.get("provider_request_id"),
                "provider_status": record.get("provider_status"),
                "submitted_at": record.get("submitted_at"),
                "confirmed_at": record.get("confirmed_at"),
                "confirmation_reference": record.get("confirmation_reference"),
                "archived_at": _iso(self.clock()),
            })
            record.update({
                "status": "RETRY_PENDING",
                "next_attempt_at": _iso(self.clock()),
                "last_error": reason,
                "provider_request_id": None,
                "provider_status": None,
                "submitted_at": None,
                "confirmed_at": None,
                "confirmation_reference": None,
                "provider_outcome_conflict": None,
            })
            self._event(record, "DELIVERY_RETRY_AUTHORIZED", actor_id, {"reason": reason})
            self._save(record)
            return self._public(record)

    def _deliver(self, record: dict[str, Any], actor_id: str) -> dict[str, Any]:
        provider = str(record["provider"])
        sender = self.senders.get(provider)
        with self._lock:
            record["status"] = "SUBMITTING"
            self._event(record, "DELIVERY_SUBMITTING", actor_id, {"provider": provider})
            self._save(record)
        try:
            if sender is None:
                raise RuntimeError("approved_delivery_connector_not_configured")
            result = dict(sender(deepcopy(record)) or {})
            request_id = str(result.get("provider_request_id") or "").strip()
            if not result.get("ok") or not request_id:
                raise RuntimeError(str(result.get("error_code") or "provider_receipt_missing"))
        except Exception as exc:
            with self._lock:
                record = self._load(str(record["workspace_id"]), str(record["delivery_id"]))
                attempts = int(record.get("attempt_count") or 0) + 1
                delay = min(86_400, 30 * (2 ** min(attempts - 1, 11)))
                record.update({
                    "status": "RETRY_PENDING", "attempt_count": attempts,
                    "next_attempt_at": _iso(self.clock() + timedelta(seconds=delay)),
                    "last_error": str(exc)[:500],
                })
                self._event(record, "DELIVERY_RETRY_PENDING", "system", {"attempt_count": attempts, "delay_seconds": delay})
                self._save(record)
                return self._public(record)
        with self._lock:
            record = self._load(str(record["workspace_id"]), str(record["delivery_id"]))
            record.update({
                "status": "SUBMITTED_TO_PROVIDER",
                "attempt_count": int(record.get("attempt_count") or 0) + 1,
                "provider_request_id": request_id,
                "provider_status": str(result.get("provider_status") or "submitted")[:120],
                "submitted_at": _iso(self.clock()), "next_attempt_at": None, "last_error": None,
            })
            self._event(record, "DELIVERY_SUBMITTED_TO_PROVIDER", actor_id, {"provider_request_id": request_id})
            self._save(record)
            self._index_provider_request(record)
            return self._public(record)

    def ingest_resend_webhook(
        self,
        raw_body: bytes,
        headers: Mapping[str, str],
        *,
        webhook_secrets: str | list[str],
        tolerance_seconds: int = 300,
    ) -> dict[str, Any]:
        """Authenticate and apply one Resend delivery event.

        Verification deliberately uses the exact request bytes.  Only bounded,
        delivery-relevant metadata is retained; recipient and message content from
        the provider payload are not copied into the callback journal.
        """

        if len(raw_body) > 1_000_000:
            raise LegalDeliveryError("resend_webhook_payload_too_large")
        event_id, timestamp = self._verify_resend_signature(
            raw_body, headers, webhook_secrets=webhook_secrets,
            tolerance_seconds=tolerance_seconds,
        )
        try:
            payload = json.loads(raw_body)
        except Exception:
            raise LegalDeliveryError("resend_webhook_json_invalid") from None
        if not isinstance(payload, dict):
            raise LegalDeliveryError("resend_webhook_payload_invalid")
        event_type = str(payload.get("type") or "").strip().lower()
        data = payload.get("data")
        if event_type not in self.RESEND_EVENT_TYPES or not isinstance(data, dict):
            return {"accepted": True, "ignored": True, "duplicate": False}
        provider_request_id = str(data.get("email_id") or "").strip()
        if not provider_request_id:
            raise LegalDeliveryError("resend_webhook_email_id_required")
        pointer = self._lookup_provider_request("resend", provider_request_id)
        if pointer is None:
            return {"accepted": True, "ignored": True, "duplicate": False}
        workspace_id = str(pointer["workspace_id"])
        delivery_id = str(pointer["delivery_id"])
        payload_hash = sha256(raw_body).hexdigest()
        with self._lock:
            record = self._load(workspace_id, delivery_id)
            if record.get("provider") != "resend" or not hmac.compare_digest(
                str(record.get("provider_request_id") or ""), provider_request_id,
            ):
                raise LegalDeliveryError("resend_webhook_provider_reference_mismatch")
            provider_events = record.setdefault("provider_events", [])
            previous = next((item for item in provider_events if item.get("event_id") == event_id), None)
            if previous is not None:
                if not hmac.compare_digest(str(previous.get("payload_sha256") or ""), payload_hash):
                    raise LegalDeliveryError("resend_webhook_event_id_conflict")
                return {
                    "accepted": True, "ignored": False, "duplicate": True,
                    "outcome": record.get("status"), "workspace_id": workspace_id,
                    "delivery_id": delivery_id,
                }

            event_record = {
                "event_id": event_id,
                "event_type": event_type,
                "provider_created_at": str(payload.get("created_at") or "")[:64] or None,
                "received_at": _iso(self.clock()),
                "signature_timestamp": timestamp,
                "payload_sha256": payload_hash,
            }
            if len(provider_events) >= 250:
                raise LegalDeliveryError("legal_delivery_provider_event_limit_reached")
            provider_events.append(event_record)

            desired = {
                "email.delivered": "DELIVERED",
                "email.delivery_delayed": "DELIVERY_DELAYED",
                "email.bounced": "BOUNCED",
                "email.failed": "REJECTED",
                "email.suppressed": "REJECTED",
            }.get(event_type)
            current = str(record.get("status") or "")
            conflict = False
            if desired in self.FINAL and current in self.FINAL and current != desired:
                conflict = True
                record["provider_outcome_conflict"] = {
                    "retained_status": current,
                    "conflicting_status": desired,
                    "event_id": event_id,
                    "event_type": event_type,
                    "detected_at": _iso(self.clock()),
                    "requires_human_review": True,
                }
                self._event(record, "DELIVERY_PROVIDER_OUTCOME_CONFLICT", "resend_webhook", event_record)
            elif desired:
                record["provider_status"] = event_type
                if desired == "DELIVERY_DELAYED" and current not in self.FINAL:
                    record["status"] = desired
                    record["last_error"] = "provider_reported_delivery_delay"
                    self._event(record, "DELIVERY_DELAYED", "resend_webhook", event_record)
                elif desired in self.FINAL:
                    record.update({
                        "status": desired,
                        "confirmed_at": _iso(self.clock()),
                        "confirmation_reference": event_id,
                        "last_error": None if desired == "DELIVERED" else event_type,
                    })
                    self._event(record, f"DELIVERY_{desired}", "resend_webhook", event_record)
            elif event_type == "email.complained":
                record["provider_status"] = event_type
                record["requires_human_review"] = True
                self._event(record, "DELIVERY_COMPLAINT_RECORDED", "resend_webhook", event_record)
            else:
                record["provider_status"] = event_type
                self._event(record, "DELIVERY_PROVIDER_EVENT_RECORDED", "resend_webhook", event_record)
            self._save(record)
            return {
                "accepted": True, "ignored": False, "duplicate": False,
                "outcome": record.get("status"), "conflict": conflict,
                "workspace_id": workspace_id, "delivery_id": delivery_id,
            }

    def refresh_provider_receipts(
        self,
        workspace_id: str,
        *,
        provider: str,
        actor_id: str,
        limit: int = 25,
    ) -> dict[str, Any]:
        """Poll one provider's authoritative delivery evidence.

        Microsoft Graph's mail submission response is not a delivery receipt.
        Exchange Message Trace is therefore read separately and applied only when
        its Internet Message-ID and recipient exactly match the encrypted outbox
        record.
        """

        provider = str(provider or "").strip().lower()
        checker = self.receipt_checkers.get(provider)
        if provider not in self.PROVIDERS or checker is None:
            raise LegalDeliveryError("delivery_receipt_checker_not_configured")
        checked_count = 0
        updated_count = 0
        not_found_count = 0
        errors: list[dict[str, str]] = []
        for item in self._records(workspace_id):
            if checked_count >= max(1, min(int(limit), 250)):
                break
            if item.get("provider") != provider or item.get("status") not in {
                "SUBMITTED_TO_PROVIDER", "DELIVERY_DELAYED",
            }:
                continue
            checked_count += 1
            try:
                result = dict(checker(deepcopy(item)) or {})
            except Exception as exc:
                errors.append({
                    "delivery_id": str(item.get("delivery_id") or ""),
                    "error_code": str(exc)[:240],
                })
                continue
            if not result.get("ok"):
                errors.append({
                    "delivery_id": str(item.get("delivery_id") or ""),
                    "error_code": str(result.get("error_code") or "receipt_lookup_failed")[:240],
                })
                continue
            if not result.get("found"):
                not_found_count += 1
                continue
            changed = self._apply_provider_receipt(
                workspace_id,
                str(item["delivery_id"]),
                provider=provider,
                actor_id=actor_id,
                result=result,
            )
            updated_count += int(changed)
        return {
            **self.status(workspace_id),
            "provider": provider,
            "checked_count": checked_count,
            "updated_count": updated_count,
            "not_found_count": not_found_count,
            "errors": errors,
        }

    def _apply_provider_receipt(
        self,
        workspace_id: str,
        delivery_id: str,
        *,
        provider: str,
        actor_id: str,
        result: Mapping[str, Any],
    ) -> bool:
        provider_status = str(result.get("provider_status") or "").strip().lower()
        trace_id = str(result.get("trace_id") or "").strip()[:500]
        observed_at = str(result.get("observed_at") or "").strip()[:64]
        internet_message_id = str(result.get("internet_message_id") or "").strip()
        if not provider_status or not trace_id or not observed_at:
            raise LegalDeliveryError("delivery_receipt_evidence_incomplete")
        event_id = "trace-" + sha256(_canonical({
            "provider": provider,
            "trace_id": trace_id,
            "provider_status": provider_status,
            "observed_at": observed_at,
        })).hexdigest()
        event_record = {
            "event_id": event_id,
            "event_type": "microsoft_graph.message_trace",
            "provider_status": provider_status,
            "provider_created_at": observed_at,
            "received_at": _iso(self.clock()),
            "provider_reference": trace_id,
            "payload_sha256": sha256(_canonical({
                "trace_id": trace_id,
                "internet_message_id": internet_message_id,
                "provider_status": provider_status,
                "observed_at": observed_at,
            })).hexdigest(),
        }
        desired = {
            "delivered": "DELIVERED",
            "failed": "REJECTED",
            "quarantined": "DELIVERY_DELAYED",
            "filteredasspam": "DELIVERY_DELAYED",
        }.get(provider_status)
        with self._lock:
            record = self._load(workspace_id, delivery_id)
            if record.get("provider") != provider:
                raise LegalDeliveryError("delivery_receipt_provider_mismatch")
            if internet_message_id and not hmac.compare_digest(
                str(record.get("provider_request_id") or ""), internet_message_id,
            ):
                raise LegalDeliveryError("delivery_receipt_provider_reference_mismatch")
            provider_events = record.setdefault("provider_events", [])
            if any(item.get("event_id") == event_id for item in provider_events):
                return False
            if len(provider_events) >= 250:
                raise LegalDeliveryError("legal_delivery_provider_event_limit_reached")
            provider_events.append(event_record)
            current = str(record.get("status") or "")
            record["provider_status"] = f"message_trace:{provider_status}"
            if desired in self.FINAL and current in self.FINAL and current != desired:
                record["provider_outcome_conflict"] = {
                    "retained_status": current,
                    "conflicting_status": desired,
                    "event_id": event_id,
                    "event_type": event_record["event_type"],
                    "detected_at": _iso(self.clock()),
                    "requires_human_review": True,
                }
                self._event(record, "DELIVERY_PROVIDER_OUTCOME_CONFLICT", actor_id, event_record)
            elif desired == "DELIVERY_DELAYED" and current not in self.FINAL:
                record.update({
                    "status": "DELIVERY_DELAYED",
                    "last_error": f"microsoft_graph_message_trace:{provider_status}",
                    "requires_human_review": True,
                })
                self._event(record, "DELIVERY_DELAYED", actor_id, event_record)
            elif desired in self.FINAL:
                record.update({
                    "status": desired,
                    "confirmed_at": _iso(self.clock()),
                    "confirmation_reference": trace_id,
                    "last_error": None if desired == "DELIVERED" else f"message_trace:{provider_status}",
                })
                self._event(record, f"DELIVERY_{desired}", actor_id, event_record)
            else:
                if provider_status not in {"gettingstatus", "pending", "expanded"}:
                    record["requires_human_review"] = True
                self._event(record, "DELIVERY_PROVIDER_EVENT_RECORDED", actor_id, event_record)
            self._save(record)
            return True

    def _index_provider_request(self, record: Mapping[str, Any]) -> None:
        provider = str(record.get("provider") or "").strip().lower()
        request_id = str(record.get("provider_request_id") or "").strip()
        if provider not in self.PROVIDERS or not request_id or len(request_id) > 1000:
            raise LegalDeliveryError("provider_request_reference_invalid")
        record_id = self._provider_index_record_id(provider, request_id)
        path = self.root / "_provider_index" / f"{record_id}.enc"
        value = {
            "schema_version": "tessaris.legal-delivery-provider-index.v1",
            "provider": provider,
            "provider_request_id": request_id,
            "workspace_id": str(record["workspace_id"]),
            "delivery_id": str(record["delivery_id"]),
            "created_at": _iso(self.clock()),
        }
        if path.exists():
            existing = self.index_store.read(
                path, workspace_id="_provider_index", record_id=record_id,
            )
            if existing.get("workspace_id") != value["workspace_id"] or existing.get("delivery_id") != value["delivery_id"]:
                raise LegalDeliveryError("provider_request_reference_collision")
            return
        self.index_store.write(
            path, value, workspace_id="_provider_index", record_id=record_id,
        )

    def _lookup_provider_request(self, provider: str, request_id: str) -> dict[str, Any] | None:
        record_id = self._provider_index_record_id(provider, request_id)
        path = self.root / "_provider_index" / f"{record_id}.enc"
        if not path.exists():
            return None
        value = self.index_store.read(path, workspace_id="_provider_index", record_id=record_id)
        if value.get("provider") != provider or not hmac.compare_digest(
            str(value.get("provider_request_id") or ""), request_id,
        ):
            raise LegalDeliveryError("provider_request_index_invalid")
        return value

    @staticmethod
    def _provider_index_record_id(provider: str, request_id: str) -> str:
        return f"provider-{sha256(f'{provider}:{request_id}'.encode('utf-8')).hexdigest()}"

    def _verify_resend_signature(
        self,
        raw_body: bytes,
        headers: Mapping[str, str],
        *,
        webhook_secrets: str | list[str],
        tolerance_seconds: int,
    ) -> tuple[str, int]:
        normalized = {str(key).lower(): str(value) for key, value in headers.items()}
        event_id = normalized.get("svix-id", "").strip()
        timestamp_text = normalized.get("svix-timestamp", "").strip()
        signature_header = normalized.get("svix-signature", "").strip()
        if not event_id or len(event_id) > 240 or not timestamp_text or not signature_header:
            raise LegalDeliveryError("resend_webhook_signature_headers_required")
        try:
            timestamp = int(timestamp_text)
        except ValueError:
            raise LegalDeliveryError("resend_webhook_timestamp_invalid") from None
        if abs(int(self.clock().timestamp()) - timestamp) > max(30, min(int(tolerance_seconds), 900)):
            raise LegalDeliveryError("resend_webhook_timestamp_outside_tolerance")
        values = [
            item.split(",", 1)[1]
            for item in signature_header.split()
            if item.startswith("v1,") and "," in item
        ]
        if not values:
            raise LegalDeliveryError("resend_webhook_signature_invalid")
        secrets_value = [webhook_secrets] if isinstance(webhook_secrets, str) else list(webhook_secrets)
        signed = f"{event_id}.{timestamp_text}.".encode("utf-8") + raw_body
        for secret in secrets_value:
            encoded = str(secret or "").strip()
            if encoded.startswith("whsec_"):
                encoded = encoded[6:]
            try:
                padding = "=" * (-len(encoded) % 4)
                key = base64.urlsafe_b64decode(encoded + padding)
            except Exception:
                continue
            expected = base64.b64encode(hmac.new(key, signed, sha256).digest()).decode("ascii")
            if any(hmac.compare_digest(expected, supplied) for supplied in values):
                return event_id, timestamp
        raise LegalDeliveryError("resend_webhook_signature_invalid")

    def _records(self, workspace_id: str) -> list[dict[str, Any]]:
        folder = self._workspace_dir(workspace_id)
        paths = bounded_record_paths(
            folder, ("delivery-*.enc",), error_type=LegalDeliveryError,
        )
        records = [self._read(path, workspace_id, path.stem) for path in paths]
        records.sort(key=lambda item: str(item.get("approved_at") or ""))
        return records

    def _load(self, workspace_id: str, delivery_id: str) -> dict[str, Any]:
        path = self._path(workspace_id, delivery_id)
        if not path.exists():
            raise LegalDeliveryError("legal_delivery_not_found")
        return self._read(path, workspace_id, delivery_id)

    def _workspace_dir(self, workspace_id: str) -> Path:
        safe = self._component(workspace_id, "workspace_id")
        path = self.root / safe
        path.mkdir(parents=True, exist_ok=True)
        os.chmod(path, 0o700)
        return path

    def _path(self, workspace_id: str, delivery_id: str) -> Path:
        delivery = self._component(delivery_id, "delivery_id")
        if not delivery.startswith("delivery-"):
            raise LegalDeliveryError("legal_delivery_not_found")
        return self._workspace_dir(workspace_id) / f"{delivery}.enc"

    def _read(self, path: Path, workspace_id: str, delivery_id: str) -> dict[str, Any]:
        value = self.store.read(path, workspace_id=workspace_id, record_id=delivery_id)
        if value.get("workspace_id") != workspace_id:
            raise LegalDeliveryError("legal_delivery_not_found")
        if not self.verify_event_chain(value):
            raise LegalDeliveryError("legal_delivery_event_chain_invalid")
        return value

    def _save(self, record: Mapping[str, Any]) -> None:
        path = self._path(str(record["workspace_id"]), str(record["delivery_id"]))
        ensure_workspace_record_write(
            workspace_folder=path.parent,
            record_path=path,
            record_patterns=("delivery-*.enc",),
            estimated_bytes=estimated_encrypted_record_bytes(record),
            error_type=LegalDeliveryError,
        )
        self.store.write(
            path, record,
            workspace_id=str(record["workspace_id"]), record_id=str(record["delivery_id"]),
        )

    def _event(self, record: dict[str, Any], event_type: str, actor_id: str, detail: Mapping[str, Any]) -> None:
        events = record.setdefault("events", [])
        if len(events) >= self.MAX_EVENTS:
            raise LegalDeliveryError("legal_delivery_event_limit_reached")
        body = {
            "event_id": f"event-{uuid4().hex}", "event_type": event_type,
            "occurred_at": _iso(self.clock()), "actor_id": str(actor_id or "unknown")[:160],
            "detail_sha256": sha256(_canonical(detail)).hexdigest(),
            "previous_hash": events[-1]["event_hash"] if events else "GENESIS",
        }
        events.append({**body, "event_hash": sha256(_canonical(body)).hexdigest()})

    @staticmethod
    def _public(record: Mapping[str, Any]) -> dict[str, Any]:
        value = deepcopy(dict(record))
        attachment = dict(value.get("attachment") or {})
        attachment.pop("content_base64", None)
        value["attachment"] = attachment
        message = dict(value.get("message") or {})
        message["body_text"] = "Signed evidence package prepared for approved delivery."
        value["message"] = message
        return value

    @staticmethod
    def _component(value: str, label: str) -> str:
        clean = str(value or "").strip()
        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        if not clean or clean in {".", ".."} or any(char not in allowed for char in clean):
            raise LegalDeliveryError(f"invalid_{label}")
        return clean
