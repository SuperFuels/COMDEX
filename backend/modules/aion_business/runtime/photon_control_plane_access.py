from __future__ import annotations

import base64
import json
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from backend.modules.aion_business.runtime.photon_billing_contracts import canonical_bytes
from backend.modules.aion_business.runtime.photon_ledger_store import PhotonLedgerStore
from backend.modules.aion_business.runtime.photon_revolut_fulfillment import PhotonRevolutFulfilment
from backend.modules.aion_business.runtime.photon_wallet_snapshot import PhotonWalletSnapshotAuthority


ACCESS_TOKEN_SCHEMA = "tessaris.photon-control-plane-token.v1"
ACCESS_AUDIT_SCHEMA = "tessaris.photon-control-plane-access-audit.v1"
TOKEN_FIELDS = {
    "schema_version", "token_id", "subject_id", "tenant_id", "scopes",
    "audience", "issued_at", "expires_at", "customer_content_included",
}
ALLOWED_SCOPES = frozenset({
    "wallet.read", "activity.read", "billing.read", "checkout.create", "refund.review",
    "pricing.manage",
})
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")


class PhotonControlPlaneAccessError(ValueError):
    pass


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise PhotonControlPlaneAccessError("photon_access_timezone_required")
    return parsed.astimezone(UTC)


def _safe(value: str, field: str) -> str:
    result = str(value or "").strip()
    if not SAFE_ID.fullmatch(result):
        raise PhotonControlPlaneAccessError(f"{field}_invalid")
    return result


@dataclass(frozen=True)
class VerifiedPhotonPrincipal:
    token_id: str
    subject_id: str
    tenant_id: str
    scopes: frozenset[str]
    expires_at: str


def issue_control_plane_token(
    *,
    token_id: str,
    subject_id: str,
    tenant_id: str,
    scopes: Iterable[str],
    issued_at: str,
    expires_at: str,
    authority_private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    scope_set = frozenset(str(scope) for scope in scopes)
    if not scope_set or not scope_set <= ALLOWED_SCOPES:
        raise PhotonControlPlaneAccessError("photon_access_scope_invalid")
    duration = (_time(expires_at) - _time(issued_at)).total_seconds()
    if duration <= 0 or duration > 3600:
        raise PhotonControlPlaneAccessError("photon_access_period_invalid")
    payload = {
        "schema_version": ACCESS_TOKEN_SCHEMA,
        "token_id": _safe(token_id, "token_id"),
        "subject_id": _safe(subject_id, "subject_id"),
        "tenant_id": _safe(tenant_id, "tenant_id"),
        "scopes": sorted(scope_set),
        "audience": "tessaris-photon-control-plane",
        "issued_at": issued_at,
        "expires_at": expires_at,
        "customer_content_included": False,
    }
    return {
        "payload": payload,
        "signature": _b64(authority_private_key.sign(canonical_bytes(payload))),
    }


def verify_control_plane_token(
    envelope: Mapping[str, Any],
    *,
    authority_public_key: Ed25519PublicKey,
    now: str,
) -> VerifiedPhotonPrincipal:
    payload = dict(envelope.get("payload") or {})
    if set(payload) != TOKEN_FIELDS or payload.get("schema_version") != ACCESS_TOKEN_SCHEMA:
        raise PhotonControlPlaneAccessError("photon_access_token_fields_invalid")
    try:
        authority_public_key.verify(
            _unb64(str(envelope.get("signature") or "")), canonical_bytes(payload)
        )
    except (InvalidSignature, ValueError) as exc:
        raise PhotonControlPlaneAccessError("photon_access_token_signature_invalid") from exc
    if payload.get("audience") != "tessaris-photon-control-plane":
        raise PhotonControlPlaneAccessError("photon_access_token_audience_invalid")
    if payload.get("customer_content_included") is not False:
        raise PhotonControlPlaneAccessError("photon_access_token_content_prohibited")
    duration = (_time(payload["expires_at"]) - _time(payload["issued_at"])).total_seconds()
    if duration <= 0 or duration > 3600:
        raise PhotonControlPlaneAccessError("photon_access_period_invalid")
    if _time(now) < _time(payload["issued_at"]) or _time(now) >= _time(payload["expires_at"]):
        raise PhotonControlPlaneAccessError("photon_access_token_not_current")
    scopes = frozenset(str(scope) for scope in payload.get("scopes") or [])
    if not scopes or not scopes <= ALLOWED_SCOPES:
        raise PhotonControlPlaneAccessError("photon_access_scope_invalid")
    return VerifiedPhotonPrincipal(
        token_id=_safe(payload["token_id"], "token_id"),
        subject_id=_safe(payload["subject_id"], "subject_id"),
        tenant_id=_safe(payload["tenant_id"], "tenant_id"),
        scopes=scopes,
        expires_at=payload["expires_at"],
    )


def encode_control_plane_bearer(envelope: Mapping[str, Any]) -> str:
    """Encode a signed envelope for an HTTP Bearer header without changing its signature."""
    raw = json.dumps(dict(envelope), sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(raw) > 8192:
        raise PhotonControlPlaneAccessError("photon_access_token_too_large")
    return _b64(raw)


def decode_control_plane_bearer(value: str) -> dict[str, Any]:
    try:
        if not value or len(value) > 12000:
            raise ValueError
        decoded = json.loads(_unb64(value).decode("utf-8"))
    except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PhotonControlPlaneAccessError("photon_access_bearer_invalid") from exc
    if not isinstance(decoded, dict) or set(decoded) != {"payload", "signature"}:
        raise PhotonControlPlaneAccessError("photon_access_bearer_invalid")
    return decoded


class PhotonControlPlaneService:
    """Tenant-bound billing use cases behind an already verified authority token."""

    def __init__(
        self,
        audit_database: str | Path,
        *,
        ledger: PhotonLedgerStore,
        wallet_snapshots: PhotonWalletSnapshotAuthority,
        revolut: PhotonRevolutFulfilment,
    ) -> None:
        candidate = Path(audit_database).expanduser()
        if candidate.is_symlink():
            raise PhotonControlPlaneAccessError("photon_access_symlink_database_forbidden")
        self.path = candidate.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        self.ledger = ledger
        self.wallet_snapshots = wallet_snapshots
        self.revolut = revolut
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS photon_control_plane_access_audit (
                    request_id TEXT PRIMARY KEY,
                    token_id TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    customer_content_included INTEGER NOT NULL CHECK (customer_content_included = 0)
                );
                CREATE TRIGGER IF NOT EXISTS photon_access_audit_no_update
                    BEFORE UPDATE ON photon_control_plane_access_audit
                    BEGIN SELECT RAISE(ABORT, 'photon_access_audit_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS photon_access_audit_no_delete
                    BEFORE DELETE ON photon_control_plane_access_audit
                    BEGIN SELECT RAISE(ABORT, 'photon_access_audit_immutable'); END;
                """
            )
        os.chmod(self.path, 0o600)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def _authorize(
        self, principal: VerifiedPhotonPrincipal, *, scope: str,
        request_id: str, action: str, recorded_at: str,
    ) -> None:
        request_id = _safe(request_id, "request_id")
        if _time(recorded_at) >= _time(principal.expires_at):
            outcome = "expired"
        elif scope not in principal.scopes:
            outcome = "denied"
        else:
            outcome = "allowed"
        self._audit(
            principal, request_id=request_id, action=action,
            outcome=outcome, recorded_at=recorded_at,
        )
        if outcome == "expired":
            raise PermissionError("photon_control_plane_token_expired")
        if outcome == "denied":
            raise PermissionError("photon_control_plane_scope_denied")

    def _audit(
        self, principal: VerifiedPhotonPrincipal, *, request_id: str,
        action: str, outcome: str, recorded_at: str,
    ) -> None:
        row = (
            _safe(request_id, "request_id"), principal.token_id, principal.subject_id,
            principal.tenant_id, _safe(action, "action"), _safe(outcome, "outcome"),
            recorded_at, ACCESS_AUDIT_SCHEMA,
        )
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT request_id, token_id, subject_id, tenant_id, action, outcome, recorded_at, schema_version FROM photon_control_plane_access_audit WHERE request_id = ?",
                (row[0],),
            ).fetchone()
            if existing:
                if tuple(existing) != row:
                    raise PhotonControlPlaneAccessError("photon_access_request_id_collision")
                raise PhotonControlPlaneAccessError("photon_access_request_replayed")
            connection.execute(
                "INSERT INTO photon_control_plane_access_audit VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)",
                row,
            )

    def wallet_snapshot(
        self, principal: VerifiedPhotonPrincipal, *, request_id: str,
        issued_at: str, valid_until: str,
    ) -> dict[str, Any]:
        self._authorize(
            principal, scope="wallet.read", request_id=request_id,
            action="wallet.snapshot", recorded_at=issued_at,
        )
        result = self.wallet_snapshots.issue(
            tenant_id=principal.tenant_id, issued_at=issued_at, valid_until=valid_until
        )
        return result

    def activity(
        self, principal: VerifiedPhotonPrincipal, *, request_id: str,
        limit: int, recorded_at: str,
    ) -> list[dict[str, Any]]:
        self._authorize(
            principal, scope="activity.read", request_id=request_id,
            action="wallet.activity", recorded_at=recorded_at,
        )
        result = self.ledger.activity(tenant_id=principal.tenant_id, limit=limit)
        return result

    def billing_records(
        self, principal: VerifiedPhotonPrincipal, *, request_id: str,
        limit: int, recorded_at: str,
    ) -> list[dict[str, Any]]:
        self._authorize(
            principal, scope="billing.read", request_id=request_id,
            action="billing.records", recorded_at=recorded_at,
        )
        return self.revolut.billing_records(
            tenant_id=principal.tenant_id, limit=limit
        )

    def commercial_status(
        self,
        principal: VerifiedPhotonPrincipal,
        *,
        request_id: str,
        recorded_at: str,
    ) -> dict[str, Any]:
        self._authorize(
            principal,
            scope="billing.read",
            request_id=request_id,
            action="billing.commercial-status",
            recorded_at=recorded_at,
        )
        return self.revolut.commercial_status(tenant_id=principal.tenant_id)

    def record_checkout_intent(
        self, principal: VerifiedPhotonPrincipal, *, request_id: str,
        order_id: str, external_reference: str, product_id: str, photons: int,
        amount_minor: int, currency: str, price_book_version: str, created_at: str,
    ) -> dict[str, Any]:
        self._authorize(
            principal, scope="checkout.create", request_id=request_id,
            action="checkout.create", recorded_at=created_at,
        )
        result = self.revolut.record_checkout_intent(
            order_id=order_id, external_reference=external_reference,
            tenant_id=principal.tenant_id, product_id=product_id, photons=photons,
            amount_minor=amount_minor, currency=currency,
            price_book_version=price_book_version, created_at=created_at,
        )
        return result
