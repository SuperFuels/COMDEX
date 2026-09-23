"""Provider-neutral commercial billing boundary with opaque vault references and receipts."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any, Dict

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash, utc_now_iso


PERMITTED_EVENTS = {
    "payment_authorized": "authorized",
    "payment_captured": "paid_active",
    "subscription_active": "paid_active",
    "payment_failed": "grace",
    "subscription_cancelled": "cancelled",
    "payment_refunded": "refunded",
}
FORBIDDEN_PAYMENT_FIELDS = {
    "card", "card_number", "pan", "cvv", "cvc", "expiry", "account_number",
    "routing_number", "iban", "password", "api_key", "access_token", "secret",
}


class PaymentBoundaryService:
    """Stores commercial intent and verified provider receipts, never payment credentials."""

    _lock = threading.RLock()

    def __init__(self, root: str | Path, *, webhook_keys: Dict[str, bytes] | None = None) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "payment_lifecycle.json"
        self.webhook_keys = dict(webhook_keys or {})

    def propose(self, *, billing_id: str, tenant_id: str, provider: str,
                customer_vault_ref: str, payment_method_vault_ref: str,
                plan: str, amount: float, currency: str, interval: str,
                offer_version: str, consent_ref: str, idempotency_key: str,
                trial_id: str = "", grace_days: int = 7) -> Dict[str, Any]:
        self._required(billing_id, tenant_id, provider, plan, currency, interval,
                       offer_version, consent_ref, idempotency_key)
        self._vault_ref(customer_vault_ref)
        self._vault_ref(payment_method_vault_ref)
        if interval not in {"month", "year", "one_time"}:
            raise ValueError("billing_interval_invalid")
        if float(amount) < 0 or not 0 <= int(grace_days) <= 90:
            raise ValueError("billing_terms_invalid")
        with self._lock:
            state = self._state()
            prior = next((row for row in state["records"] if row["idempotency_hash"] == canonical_hash(idempotency_key)), None)
            if prior:
                if prior["billing_id"] != billing_id:
                    raise ValueError("billing_idempotency_conflict")
                return dict(prior)
            if any(row["billing_id"] == billing_id for row in state["records"]):
                raise ValueError("billing_id_reused")
            record = {
                "schema_version": "aion.payment_lifecycle.v1", "billing_id": billing_id,
                "tenant_id": tenant_id, "provider": provider, "state": "proposed",
                "customer_vault_ref": customer_vault_ref,
                "payment_method_vault_ref": payment_method_vault_ref,
                "plan": plan, "amount": round(float(amount), 2), "currency": currency.upper(),
                "interval": interval, "offer_version": offer_version,
                "trial_id": trial_id or None, "grace_days": int(grace_days),
                "consent_receipt_hash": canonical_hash(consent_ref),
                "idempotency_hash": canonical_hash(idempotency_key),
                "provider_events": [], "customer_content_stored": False,
                "created_at": utc_now_iso(), "updated_at": utc_now_iso(),
            }
            state["records"].append(record)
            self._write(state)
            return dict(record)

    def approve(self, *, billing_id: str, actor_id: str, approval_ref: str,
                expected_plan: str, expected_amount: float, expected_currency: str) -> Dict[str, Any]:
        self._required(actor_id, approval_ref, expected_plan, expected_currency)
        with self._lock:
            state, record = self._record(billing_id)
            if record["state"] != "proposed":
                raise ValueError("billing_not_approvable")
            if (record["plan"], record["amount"], record["currency"]) != (
                expected_plan, round(float(expected_amount), 2), expected_currency.upper()
            ):
                raise PermissionError("billing_exact_terms_mismatch")
            record.update({"state": "approved_pending_provider", "approved_by": actor_id,
                           "approval_receipt_hash": canonical_hash(approval_ref), "updated_at": utc_now_iso()})
            self._write(state)
            return self.public_status(billing_id)

    def cancel(self, *, billing_id: str, actor_id: str, cancellation_ref: str) -> Dict[str, Any]:
        self._required(actor_id, cancellation_ref)
        with self._lock:
            state, record = self._record(billing_id)
            if record["state"] in {"cancelled", "refunded"}:
                return self.public_status(billing_id)
            record.update({"state": "cancellation_pending_provider", "cancelled_by": actor_id,
                           "cancellation_receipt_hash": canonical_hash(cancellation_ref), "updated_at": utc_now_iso()})
            self._write(state)
            return self.public_status(billing_id)

    def accept_provider_event(self, *, provider: str, event_id: str, event_type: str,
                              billing_id: str, provider_object_ref: str,
                              occurred_at: str, signature: str) -> Dict[str, Any]:
        self._required(provider, event_id, event_type, billing_id, provider_object_ref, occurred_at, signature)
        if event_type not in PERMITTED_EVENTS:
            raise ValueError("provider_event_type_invalid")
        key = self.webhook_keys.get(provider)
        if not key:
            raise PermissionError("payment_provider_not_configured")
        payload = {"provider": provider, "event_id": event_id, "event_type": event_type,
                   "billing_id": billing_id, "provider_object_ref": provider_object_ref,
                   "occurred_at": occurred_at}
        expected = hmac.new(key, canonical_bytes(payload), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise PermissionError("provider_event_signature_invalid")
        with self._lock:
            state, record = self._record(billing_id)
            if record["provider"] != provider:
                raise PermissionError("payment_provider_mismatch")
            prior = next((row for row in record["provider_events"] if row["event_id_hash"] == canonical_hash(event_id)), None)
            if prior:
                return dict(prior)
            event = {"event_id_hash": canonical_hash(event_id), "event_type": event_type,
                     "provider_object_hash": canonical_hash(provider_object_ref),
                     "occurred_at": occurred_at, "accepted_at": utc_now_iso()}
            event["receipt_hash"] = canonical_hash(event)
            record["provider_events"].append(event)
            record.update({"state": PERMITTED_EVENTS[event_type], "updated_at": utc_now_iso()})
            self._write(state)
            return dict(event)

    def public_status(self, billing_id: str) -> Dict[str, Any]:
        _, record = self._record(billing_id)
        return {key: value for key, value in record.items()
                if key not in {"customer_vault_ref", "payment_method_vault_ref", "provider_events"}}

    @staticmethod
    def sign_test_event(key: bytes, payload: Dict[str, Any]) -> str:
        return hmac.new(key, canonical_bytes(payload), hashlib.sha256).hexdigest()

    @staticmethod
    def _required(*values: Any) -> None:
        if any(not str(value or "").strip() for value in values):
            raise ValueError("required_value_missing")

    @staticmethod
    def _vault_ref(value: str) -> None:
        if not str(value).startswith("vault://") or len(str(value)) > 256:
            raise ValueError("opaque_vault_reference_required")

    def _record(self, billing_id: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
        state = self._state()
        record = next((row for row in state["records"] if row["billing_id"] == billing_id), None)
        if not record:
            raise KeyError("billing_record_not_found")
        return state, record

    def _state(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": "aion.payment_lifecycles.v1", "records": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, state: Dict[str, Any]) -> None:
        material = json.dumps(state, sort_keys=True).lower()
        if any(f'"{field}"' in material for field in FORBIDDEN_PAYMENT_FIELDS):
            raise ValueError("raw_payment_or_secret_field_forbidden")
        temporary = self.path.with_suffix(f".{uuid.uuid4().hex}.tmp")
        temporary.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)
