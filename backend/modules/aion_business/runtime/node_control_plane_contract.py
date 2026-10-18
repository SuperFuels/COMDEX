from __future__ import annotations

import base64
import hashlib
import json
import re
import sqlite3
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


CERTIFICATE_SCHEMA = "tessaris.node-certificate.v1"
CERTIFICATE_REVOCATION_SCHEMA = "tessaris.node-certificate-revocation.v1"
HEARTBEAT_SCHEMA = "tessaris.node-heartbeat.v1"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
ALLOWED_HEARTBEAT_KEYS = {
    "schema_version", "node_id", "tenant_id", "sequence", "issued_at",
    "platform_class", "architecture", "update_channel", "components", "checks",
}
PROHIBITED_SCOPE_WORDS = {"vault.read", "vault.write", "shell", "remote_control", "file.read", "file.write"}
PLATFORM_CLASSES = {"desktop-only", "node-capable", "compute-worker-capable"}
ARCHITECTURES = {"x86_64", "arm64"}
UPDATE_CHANNELS = {"stable", "preview", "lts", "offline"}
HEALTH_STATES = {"healthy", "degraded", "unavailable", "unknown"}
COMPONENT_KEYS = {"node", "guardian", "desktop", "secure-link", "updater", "billing"}
CHECK_KEYS = COMPONENT_KEYS | {"backup", "entitlement", "storage"}
VERSION_VALUE = re.compile(r"^[0-9][0-9A-Za-z.+_-]{0,31}$")
CERTIFICATE_KEYS = {
    "schema_version", "node_id", "tenant_id", "node_public_key", "platform_class",
    "architecture", "approved_by", "issued_at", "expires_at", "scopes", "explicitly_prohibited",
}
CERTIFICATE_REVOCATION_KEYS = {
    "schema_version", "certificate_fingerprint", "node_id", "tenant_id",
    "revoked_at", "reason_code",
}
REVOCATION_REASON_CODES = {
    "device_lost", "device_replaced", "key_compromised", "membership_removed",
    "installation_retired", "security_response",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("node_time_timezone_required")
    return parsed.astimezone(UTC)


def node_certificate_fingerprint(envelope: Mapping[str, Any]) -> str:
    """Return a stable public identifier for one exact signed certificate."""

    payload = dict(envelope.get("payload") or {})
    signature = str(envelope.get("signature") or "")
    if not payload or not signature:
        raise NodeControlPlaneError("node_certificate_envelope_invalid")
    return hashlib.sha256(_canonical({"payload": payload, "signature": signature})).hexdigest()


class NodeControlPlaneError(ValueError):
    pass


def issue_node_certificate(
    request: Mapping[str, Any],
    *,
    authority_private_key: Ed25519PrivateKey,
    approved_by: str,
    issued_at: str,
    expires_at: str,
) -> dict[str, Any]:
    node_id = str(request.get("node_id") or "")
    tenant_id = str(request.get("tenant_id") or "")
    approved_by = str(approved_by or "")
    if not all(SAFE_ID.fullmatch(value) for value in (node_id, tenant_id, approved_by)):
        raise NodeControlPlaneError("node_certificate_identity_invalid")
    public_key = str(request.get("node_public_key") or "")
    try:
        if len(_unb64(public_key)) != 32:
            raise ValueError
    except Exception as exc:
        raise NodeControlPlaneError("node_public_key_invalid") from exc
    if _time(expires_at) <= _time(issued_at):
        raise NodeControlPlaneError("node_certificate_expiry_invalid")
    if request.get("platform_class") not in PLATFORM_CLASSES or request.get("architecture") not in ARCHITECTURES:
        raise NodeControlPlaneError("node_certificate_capability_invalid")
    payload = {
        "schema_version": CERTIFICATE_SCHEMA,
        "node_id": node_id,
        "tenant_id": tenant_id,
        "node_public_key": public_key,
        "platform_class": str(request.get("platform_class") or ""),
        "architecture": str(request.get("architecture") or ""),
        "approved_by": approved_by,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "scopes": ["health.publish", "release.read", "entitlement.read"],
        "explicitly_prohibited": sorted(PROHIBITED_SCOPE_WORDS),
    }
    return {"payload": payload, "signature": _b64(authority_private_key.sign(_canonical(payload)))}


def verify_node_certificate(
    envelope: Mapping[str, Any], *, authority_public_key: Ed25519PublicKey, now: str
) -> dict[str, Any]:
    payload = dict(envelope.get("payload") or {})
    if set(payload) != CERTIFICATE_KEYS or payload.get("schema_version") != CERTIFICATE_SCHEMA:
        raise NodeControlPlaneError("node_certificate_schema_invalid")
    try:
        authority_public_key.verify(_unb64(str(envelope.get("signature") or "")), _canonical(payload))
    except (InvalidSignature, ValueError) as exc:
        raise NodeControlPlaneError("node_certificate_signature_invalid") from exc
    if _time(now) < _time(payload["issued_at"]) or _time(now) >= _time(payload["expires_at"]):
        raise NodeControlPlaneError("node_certificate_not_current")
    if set(payload.get("scopes") or []) & PROHIBITED_SCOPE_WORDS:
        raise NodeControlPlaneError("node_certificate_scope_prohibited")
    if payload.get("scopes") != ["health.publish", "release.read", "entitlement.read"]:
        raise NodeControlPlaneError("node_certificate_scope_invalid")
    if payload.get("explicitly_prohibited") != sorted(PROHIBITED_SCOPE_WORDS):
        raise NodeControlPlaneError("node_certificate_prohibitions_invalid")
    if not all(
        SAFE_ID.fullmatch(str(payload.get(key) or ""))
        for key in ("node_id", "tenant_id", "approved_by")
    ):
        raise NodeControlPlaneError("node_certificate_identity_invalid")
    if (
        payload.get("platform_class") not in PLATFORM_CLASSES
        or payload.get("architecture") not in ARCHITECTURES
    ):
        raise NodeControlPlaneError("node_certificate_capability_invalid")
    return payload


def issue_node_certificate_revocation(
    certificate: Mapping[str, Any],
    *,
    authority_private_key: Ed25519PrivateKey,
    node_id: str,
    tenant_id: str,
    revoked_at: str,
    reason_code: str,
) -> dict[str, Any]:
    """Create an authority-signed, content-free revocation for one certificate."""

    if not SAFE_ID.fullmatch(str(node_id or "")) or not SAFE_ID.fullmatch(str(tenant_id or "")):
        raise NodeControlPlaneError("node_certificate_revocation_identity_invalid")
    _time(revoked_at)
    if reason_code not in REVOCATION_REASON_CODES:
        raise NodeControlPlaneError("node_certificate_revocation_reason_invalid")
    payload = {
        "schema_version": CERTIFICATE_REVOCATION_SCHEMA,
        "certificate_fingerprint": node_certificate_fingerprint(certificate),
        "node_id": str(node_id),
        "tenant_id": str(tenant_id),
        "revoked_at": str(revoked_at),
        "reason_code": str(reason_code),
    }
    return {"payload": payload, "signature": _b64(authority_private_key.sign(_canonical(payload)))}


def verify_node_certificate_revocation(
    envelope: Mapping[str, Any], *, authority_public_key: Ed25519PublicKey, now: str
) -> dict[str, Any]:
    payload = dict(envelope.get("payload") or {})
    if (
        set(payload) != CERTIFICATE_REVOCATION_KEYS
        or payload.get("schema_version") != CERTIFICATE_REVOCATION_SCHEMA
    ):
        raise NodeControlPlaneError("node_certificate_revocation_schema_invalid")
    try:
        authority_public_key.verify(
            _unb64(str(envelope.get("signature") or "")), _canonical(payload)
        )
    except (InvalidSignature, ValueError) as exc:
        raise NodeControlPlaneError("node_certificate_revocation_signature_invalid") from exc
    if not re.fullmatch(r"[0-9a-f]{64}", str(payload.get("certificate_fingerprint") or "")):
        raise NodeControlPlaneError("node_certificate_revocation_fingerprint_invalid")
    if not all(
        SAFE_ID.fullmatch(str(payload.get(key) or "")) for key in ("node_id", "tenant_id")
    ):
        raise NodeControlPlaneError("node_certificate_revocation_identity_invalid")
    if payload.get("reason_code") not in REVOCATION_REASON_CODES:
        raise NodeControlPlaneError("node_certificate_revocation_reason_invalid")
    if _time(str(payload.get("revoked_at") or "")) > _time(now):
        raise NodeControlPlaneError("node_certificate_revocation_from_future")
    return payload


def _validated_heartbeat_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(payload)
    if set(value) != ALLOWED_HEARTBEAT_KEYS:
        raise NodeControlPlaneError("node_heartbeat_fields_invalid")
    if value.get("schema_version") != HEARTBEAT_SCHEMA or int(value.get("sequence") or 0) <= 0:
        raise NodeControlPlaneError("node_heartbeat_contract_invalid")
    if value.get("platform_class") not in PLATFORM_CLASSES or value.get("architecture") not in ARCHITECTURES or value.get("update_channel") not in UPDATE_CHANNELS:
        raise NodeControlPlaneError("node_heartbeat_status_invalid")
    components = value.get("components")
    checks = value.get("checks")
    if not isinstance(components, dict) or not set(components).issubset(COMPONENT_KEYS):
        raise NodeControlPlaneError("node_heartbeat_status_invalid")
    if any(not VERSION_VALUE.fullmatch(str(item)) for item in components.values()):
        raise NodeControlPlaneError("node_heartbeat_status_invalid")
    if not isinstance(checks, dict) or not set(checks).issubset(CHECK_KEYS):
        raise NodeControlPlaneError("node_heartbeat_status_invalid")
    if any(str(item) not in HEALTH_STATES for item in checks.values()):
        raise NodeControlPlaneError("node_heartbeat_status_invalid")
    if not all(
        SAFE_ID.fullmatch(str(value.get(key) or ""))
        for key in ("node_id", "tenant_id")
    ):
        raise NodeControlPlaneError("node_heartbeat_identity_invalid")
    _time(str(value.get("issued_at") or ""))
    return value


def sign_node_heartbeat(payload: Mapping[str, Any], *, node_private_key: Ed25519PrivateKey) -> dict[str, Any]:
    value = _validated_heartbeat_payload(payload)
    return {"payload": value, "signature": _b64(node_private_key.sign(_canonical(value)))}


class NodeHeartbeatRegistry:
    """Hosted content-free replay boundary; it has no command or vault API."""

    def __init__(
        self,
        database: str | Path,
        *,
        max_nodes: int = 100_000,
        maximum_heartbeat_age_seconds: int = 900,
    ) -> None:
        requested = Path(database).expanduser()
        if requested.is_symlink():
            raise NodeControlPlaneError("node_heartbeat_registry_path_unsafe")
        self.database = requested.resolve()
        self.max_nodes = max(1, min(int(max_nodes), 1_000_000))
        self.maximum_heartbeat_age_seconds = max(
            30, min(int(maximum_heartbeat_age_seconds), 86_400)
        )
        self.database.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.database.parent, 0o700)
        except OSError:
            pass
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS node_heartbeat_sequence (tenant_id TEXT, node_id TEXT, last_sequence INTEGER NOT NULL, last_issued_at TEXT NOT NULL, PRIMARY KEY (tenant_id, node_id))"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS node_certificate_revocation (certificate_fingerprint TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, node_id TEXT NOT NULL, revoked_at TEXT NOT NULL, reason_code TEXT NOT NULL)"
            )
        try:
            os.chmod(self.database, 0o600)
        except OSError:
            pass

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.database), timeout=5.0, isolation_level=None
        )
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def accept(
        self,
        heartbeat: Mapping[str, Any],
        *,
        certificate: Mapping[str, Any],
        authority_public_key: Ed25519PublicKey,
        now: str,
    ) -> dict[str, Any]:
        cert = verify_node_certificate(certificate, authority_public_key=authority_public_key, now=now)
        certificate_fingerprint = node_certificate_fingerprint(certificate)
        with self._connect() as connection:
            revoked = connection.execute(
                "SELECT 1 FROM node_certificate_revocation WHERE certificate_fingerprint = ?",
                (certificate_fingerprint,),
            ).fetchone()
        if revoked is not None:
            raise NodeControlPlaneError("node_certificate_revoked")
        payload = _validated_heartbeat_payload(heartbeat.get("payload") or {})
        if payload.get("node_id") != cert["node_id"] or payload.get("tenant_id") != cert["tenant_id"]:
            raise NodeControlPlaneError("node_heartbeat_identity_mismatch")
        if payload.get("platform_class") != cert["platform_class"] or payload.get("architecture") != cert["architecture"]:
            raise NodeControlPlaneError("node_heartbeat_capability_mismatch")
        if _time(payload["issued_at"]) > _time(now):
            raise NodeControlPlaneError("node_heartbeat_from_future")
        if (
            _time(now) - _time(payload["issued_at"])
        ).total_seconds() > self.maximum_heartbeat_age_seconds:
            raise NodeControlPlaneError("node_heartbeat_stale")
        try:
            public_key = Ed25519PublicKey.from_public_bytes(_unb64(cert["node_public_key"]))
            public_key.verify(_unb64(str(heartbeat.get("signature") or "")), _canonical(payload))
        except (InvalidSignature, ValueError) as exc:
            raise NodeControlPlaneError("node_heartbeat_signature_invalid") from exc
        sequence = int(payload.get("sequence") or 0)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT last_sequence FROM node_heartbeat_sequence WHERE tenant_id = ? AND node_id = ?",
                (cert["tenant_id"], cert["node_id"]),
            ).fetchone()
            if sequence <= (int(current[0]) if current else 0):
                connection.rollback()
                raise NodeControlPlaneError("node_heartbeat_replayed")
            if current is None:
                count = int(connection.execute(
                    "SELECT COUNT(*) FROM node_heartbeat_sequence"
                ).fetchone()[0])
                if count >= self.max_nodes:
                    connection.rollback()
                    raise NodeControlPlaneError(
                        "node_heartbeat_registry_capacity_exceeded"
                    )
            connection.execute(
                "INSERT INTO node_heartbeat_sequence (tenant_id, node_id, last_sequence, last_issued_at) VALUES (?, ?, ?, ?) ON CONFLICT(tenant_id, node_id) DO UPDATE SET last_sequence = excluded.last_sequence, last_issued_at = excluded.last_issued_at",
                (cert["tenant_id"], cert["node_id"], sequence, payload["issued_at"]),
            )
            connection.commit()
        return {
            "accepted": True,
            "node_id": cert["node_id"],
            "tenant_id": cert["tenant_id"],
            "sequence": sequence,
            "content_free": True,
        }

    def apply_revocation(
        self,
        revocation: Mapping[str, Any],
        *,
        authority_public_key: Ed25519PublicKey,
        now: str,
    ) -> dict[str, Any]:
        """Persist a verified revocation before any later heartbeat is accepted."""

        payload = verify_node_certificate_revocation(
            revocation, authority_public_key=authority_public_key, now=now
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT tenant_id, node_id, revoked_at, reason_code FROM node_certificate_revocation WHERE certificate_fingerprint = ?",
                (payload["certificate_fingerprint"],),
            ).fetchone()
            expected = (
                payload["tenant_id"], payload["node_id"],
                payload["revoked_at"], payload["reason_code"],
            )
            if existing is not None and tuple(existing) != expected:
                connection.rollback()
                raise NodeControlPlaneError("node_certificate_revocation_conflict")
            connection.execute(
                "INSERT OR IGNORE INTO node_certificate_revocation (certificate_fingerprint, tenant_id, node_id, revoked_at, reason_code) VALUES (?, ?, ?, ?, ?)",
                (payload["certificate_fingerprint"], *expected),
            )
            connection.commit()
        return {
            "revoked": True,
            "certificate_fingerprint": payload["certificate_fingerprint"],
            "node_id": payload["node_id"],
            "tenant_id": payload["tenant_id"],
            "reason_code": payload["reason_code"],
            "content_free": True,
        }
