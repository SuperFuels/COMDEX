from __future__ import annotations

import os
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from backend.modules.aion_business.runtime.photon_control_plane_access import (
    PhotonControlPlaneAccessError,
    VerifiedPhotonPrincipal,
)


PRICING_ADMIN_AUDIT_SCHEMA = "tessaris.photon-pricing-admin-audit.v1"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")
SAFE_HASH = re.compile(r"^[0-9a-f]{64}$")


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise PhotonControlPlaneAccessError("photon_pricing_admin_timezone_required")
    return parsed.astimezone(UTC)


def _safe(value: str, field: str) -> str:
    result = str(value or "").strip()
    if not SAFE_ID.fullmatch(result):
        raise PhotonControlPlaneAccessError(f"{field}_invalid")
    return result


class PhotonPricingAdminAudit:
    """Immutable, content-free authority log for hosted founder pricing actions."""

    def __init__(self, database_path: str | Path) -> None:
        candidate = Path(database_path).expanduser()
        if candidate.is_symlink():
            raise ValueError("photon_pricing_admin_symlink_database_forbidden")
        self.path = candidate.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS photon_pricing_admin_audit (
                    request_id TEXT PRIMARY KEY,
                    token_id TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    platform_tenant_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    price_book_version TEXT NOT NULL,
                    preview_hash TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    customer_content_included INTEGER NOT NULL CHECK (customer_content_included = 0)
                );
                CREATE TRIGGER IF NOT EXISTS photon_pricing_admin_audit_no_update
                    BEFORE UPDATE ON photon_pricing_admin_audit
                    BEGIN SELECT RAISE(ABORT, 'photon_pricing_admin_audit_immutable'); END;
                CREATE TRIGGER IF NOT EXISTS photon_pricing_admin_audit_no_delete
                    BEFORE DELETE ON photon_pricing_admin_audit
                    BEGIN SELECT RAISE(ABORT, 'photon_pricing_admin_audit_immutable'); END;
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

    def authorize(
        self,
        principal: VerifiedPhotonPrincipal,
        *,
        platform_tenant_id: str,
        request_id: str,
        action: str,
        price_book_version: str,
        preview_hash: str,
        recorded_at: str,
        reauthentication_required: bool = False,
        reauthenticated: bool = False,
    ) -> None:
        request_id = _safe(request_id, "request_id")
        platform_tenant_id = _safe(platform_tenant_id, "platform_tenant_id")
        version = _safe(price_book_version, "price_book_version")
        preview_hash = str(preview_hash or "").strip()
        if preview_hash and not SAFE_HASH.fullmatch(preview_hash):
            raise PhotonControlPlaneAccessError("photon_price_preview_hash_invalid")
        if _time(recorded_at) >= _time(principal.expires_at):
            outcome = "expired"
        elif principal.tenant_id != platform_tenant_id:
            outcome = "wrong_platform_tenant"
        elif "pricing.manage" not in principal.scopes:
            outcome = "scope_denied"
        elif reauthentication_required and not reauthenticated:
            outcome = "reauthentication_denied"
        else:
            outcome = "allowed"
        row = (
            request_id,
            principal.token_id,
            principal.subject_id,
            platform_tenant_id,
            _safe(action, "action"),
            outcome,
            version,
            preview_hash,
            recorded_at,
            PRICING_ADMIN_AUDIT_SCHEMA,
        )
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT request_id, token_id, subject_id, platform_tenant_id,
                       action, outcome, price_book_version, preview_hash,
                       recorded_at, schema_version
                FROM photon_pricing_admin_audit WHERE request_id = ?
                """,
                (request_id,),
            ).fetchone()
            if existing:
                if tuple(existing) != row:
                    raise PhotonControlPlaneAccessError(
                        "photon_pricing_admin_request_id_collision"
                    )
                raise PhotonControlPlaneAccessError(
                    "photon_pricing_admin_request_replayed"
                )
            connection.execute(
                """
                INSERT INTO photon_pricing_admin_audit
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                row,
            )
        if outcome == "expired":
            raise PermissionError("photon_pricing_admin_token_expired")
        if outcome == "wrong_platform_tenant":
            raise PermissionError("photon_pricing_admin_tenant_denied")
        if outcome == "scope_denied":
            raise PermissionError("photon_pricing_admin_scope_denied")
        if outcome == "reauthentication_denied":
            raise PermissionError("photon_pricing_admin_reauthentication_required")
