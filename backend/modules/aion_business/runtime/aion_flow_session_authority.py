"""Short-lived, body-bound desktop sessions for AION Flow HTTP operations."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import hmac
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
from typing import Mapping

from backend.modules.aion_business.runtime.application_account_recovery import (
    ApplicationAccountRecoveryStore,
)
from backend.modules.aion_business.runtime.application_account_descriptor_registry import (
    ApplicationAccountDescriptorRegistry,
    ApplicationAccountDescriptorRegistryClient,
)


SESSION_HEADERS = {
    "device_id": "x-aion-flow-device-id",
    "person_id": "x-aion-flow-person-id",
    "workspace_id": "x-aion-flow-workspace-id",
    "issued_at": "x-aion-flow-issued-at",
    "nonce": "x-aion-flow-nonce",
    "body_hash": "x-aion-flow-body-sha256",
    "signature": "x-aion-flow-signature",
}

ACCOUNT_SESSION_HEADERS = {
    "account_id": "x-tessaris-account-id",
    "recovery_epoch": "x-tessaris-recovery-epoch",
}


@dataclass(frozen=True)
class VerifiedAionFlowSession:
    device_id: str
    person_id: str
    workspace_id: str
    issued_at: int
    nonce: str
    account_id: str | None = None
    recovery_epoch: int | None = None

    def actor(self) -> dict[str, str]:
        actor = {
            "person_id": self.person_id,
            "workspace_id": self.workspace_id,
            "organisation_id": self.workspace_id,
            "role": "canonical_authority",
            "authority_source": "signed_desktop_session+canonical_organisation.v1",
        }
        if self.account_id is not None:
            actor.update({
                "account_id": self.account_id,
                "account_recovery_epoch": str(self.recovery_epoch),
                "authority_source": (
                    "signed_desktop_session+application_account_epoch+"
                    "canonical_organisation.v2"
                ),
            })
        return actor


class AionFlowSessionAuthority:
    """Verify requests signed by the installed desktop shell.

    The secret never enters renderer JavaScript.  Electron signs the exact HTTP
    method, target and serialized body through an IPC method.  Canonical
    organisation membership is checked separately after this possession proof.
    """

    def __init__(
        self,
        *,
        key_path: str | Path | None = None,
        secret: bytes | None = None,
        clock=time.time,
        maximum_age_seconds: int = 60,
        replay_store_path: str | Path | None = None,
        persistent_replay: bool | None = None,
        maximum_replay_entries: int = 100_000,
        account_recovery_store: ApplicationAccountRecoveryStore | None = None,
        account_descriptor_registry: (
            ApplicationAccountDescriptorRegistry | ApplicationAccountDescriptorRegistryClient | None
        ) = None,
        account_recovery_root: str | Path | None = None,
        enforce_account_recovery: bool | None = None,
    ) -> None:
        self.key_path = Path(key_path or os.environ.get("TESSARIS_AION_FLOW_SESSION_KEY_PATH") or Path.home() / ".tessaris/security/aion-flow-desktop-session.key")
        self._explicit_secret = secret
        self.clock = clock
        self.maximum_age_seconds = max(10, min(int(maximum_age_seconds), 300))
        self.persistent_replay = (secret is None) if persistent_replay is None else bool(persistent_replay)
        self.replay_store_path = Path(
            replay_store_path
            or os.environ.get("TESSARIS_AION_FLOW_REPLAY_STORE_PATH")
            or self.key_path.with_suffix(".replay.sqlite3")
        )
        self.maximum_replay_entries = max(100, min(int(maximum_replay_entries), 1_000_000))
        recovery_root = Path(
            account_recovery_root
            or os.environ.get("TESSARIS_APPLICATION_ACCOUNT_RECOVERY_DIR")
            or Path.home() / ".tessaris/security/application-account-recovery"
        )
        self.account_recovery_store = account_recovery_store or ApplicationAccountRecoveryStore(
            recovery_root
        )
        registry_url = str(os.environ.get("TESSARIS_ACCOUNT_DESCRIPTOR_REGISTRY_URL") or "").strip()
        if account_descriptor_registry is not None:
            self.account_descriptor_registry = account_descriptor_registry
        elif registry_url:
            registry_cache_root = Path(
                os.environ.get("TESSARIS_ACCOUNT_DESCRIPTOR_REGISTRY_CACHE_DIR")
                or Path.home() / ".tessaris/security/application-account-registry-cache"
            )
            self.account_descriptor_registry = ApplicationAccountDescriptorRegistryClient(
                registry_url,
                cache_root=registry_cache_root,
            )
        else:
            self.account_descriptor_registry = None
        self.enforce_account_recovery = enforce_account_recovery
        self._nonces: dict[str, int] = {}
        self._lock = threading.Lock()

    def verify(self, *, method: str, target: str, body: bytes, headers: Mapping[str, str]) -> VerifiedAionFlowSession:
        return self.verify_body_hash(
            method=method,
            target=target,
            body_hash=sha256(body).hexdigest(),
            headers=headers,
        )

    def verify_body_hash(
        self,
        *,
        method: str,
        target: str,
        body_hash: str,
        headers: Mapping[str, str],
    ) -> VerifiedAionFlowSession:
        """Verify a precomputed digest for a body streamed under an explicit cap."""

        values = {name: str(headers.get(header) or "").strip() for name, header in SESSION_HEADERS.items()}
        if any(not values[name] for name in SESSION_HEADERS):
            raise PermissionError("signed_aion_flow_session_required")
        for name in ("device_id", "person_id", "workspace_id"):
            if len(values[name]) > 160 or any(ord(char) < 32 for char in values[name]):
                raise PermissionError("signed_aion_flow_session_identity_invalid")
        if not re.fullmatch(r"[0-9a-f]{64}", values["body_hash"]):
            raise PermissionError("signed_aion_flow_session_body_hash_invalid")
        if not re.fullmatch(r"[0-9a-f]{64}", values["signature"]):
            raise PermissionError("signed_aion_flow_session_signature_invalid")
        try:
            issued_at = int(values["issued_at"])
        except ValueError as exc:
            raise PermissionError("signed_aion_flow_session_timestamp_invalid") from exc
        now = int(self.clock())
        if issued_at > now + 5 or now - issued_at > self.maximum_age_seconds:
            raise PermissionError("signed_aion_flow_session_expired")
        if not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", values["nonce"]):
            raise PermissionError("signed_aion_flow_session_nonce_invalid")
        if not str(target).startswith("/") or len(str(target)) > 4096:
            raise PermissionError("signed_aion_flow_session_target_invalid")
        actual_body_hash = str(body_hash or "").strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", actual_body_hash):
            raise PermissionError("signed_aion_flow_session_body_hash_invalid")
        if not hmac.compare_digest(actual_body_hash, values["body_hash"]):
            raise PermissionError("signed_aion_flow_session_body_changed")
        account_enforced = self._account_recovery_is_enforced()
        account_id = str(headers.get(ACCOUNT_SESSION_HEADERS["account_id"]) or "").strip()
        raw_epoch = str(headers.get(ACCOUNT_SESSION_HEADERS["recovery_epoch"]) or "").strip()
        recovery_epoch: int | None = None
        if account_enforced:
            if not account_id or not raw_epoch:
                raise PermissionError("signed_aion_flow_session_account_epoch_required")
            if not re.fullmatch(r"account_[0-9a-f]{40}", account_id):
                raise PermissionError("signed_aion_flow_session_account_id_invalid")
            try:
                recovery_epoch = int(raw_epoch)
            except ValueError as exc:
                raise PermissionError("signed_aion_flow_session_account_epoch_invalid") from exc
            if recovery_epoch < 1:
                raise PermissionError("signed_aion_flow_session_account_epoch_invalid")
        elif account_id or raw_epoch:
            raise PermissionError("signed_aion_flow_session_account_registry_unavailable")
        message = self.message(
            method=method,
            target=target,
            body_hash=values["body_hash"],
            device_id=values["device_id"],
            person_id=values["person_id"],
            workspace_id=values["workspace_id"],
            issued_at=issued_at,
            nonce=values["nonce"],
            account_id=account_id or None,
            recovery_epoch=recovery_epoch,
        )
        expected = hmac.new(self._secret(), message, sha256).hexdigest()
        if not hmac.compare_digest(expected, values["signature"]):
            raise PermissionError("signed_aion_flow_session_invalid")
        if account_enforced:
            if self.account_descriptor_registry is not None:
                authorised = self.account_descriptor_registry.authorize_device(
                    account_id=account_id,
                    device_id=values["device_id"],
                    recovery_epoch=int(recovery_epoch),
                    workspace_id=values["workspace_id"],
                )
            else:
                authorised = self.account_recovery_store.authorize_device(
                    device_id=values["device_id"], recovery_epoch=int(recovery_epoch),
                )
            if not hmac.compare_digest(str(authorised["account_id"]), account_id):
                raise PermissionError("signed_aion_flow_session_account_mismatch")
            if not hmac.compare_digest(str(authorised["workspace_id"]), values["workspace_id"]):
                raise PermissionError("signed_aion_flow_session_account_workspace_mismatch")
        self._remember_nonce(
            device_id=values["device_id"], nonce=values["nonce"],
            issued_at=issued_at, now=now,
        )
        return VerifiedAionFlowSession(
            device_id=values["device_id"], person_id=values["person_id"],
            workspace_id=values["workspace_id"], issued_at=issued_at, nonce=values["nonce"],
            account_id=account_id or None, recovery_epoch=recovery_epoch,
        )

    def sign_for_test(self, *, method: str, target: str, body: bytes, device_id: str, person_id: str, workspace_id: str, issued_at: int | None = None, nonce: str | None = None, account_id: str | None = None, recovery_epoch: int | None = None) -> dict[str, str]:
        issued = int(self.clock()) if issued_at is None else int(issued_at)
        value = nonce or secrets.token_hex(16)
        body_hash = sha256(body).hexdigest()
        if self._account_recovery_is_enforced() and (account_id is None or recovery_epoch is None):
            descriptor = self.account_recovery_store.descriptor()
            account_id = str(descriptor["account_id"])
            recovery_epoch = int(descriptor["recovery_epoch"])
        signature = hmac.new(self._secret(), self.message(method=method, target=target, body_hash=body_hash, device_id=device_id, person_id=person_id, workspace_id=workspace_id, issued_at=issued, nonce=value, account_id=account_id, recovery_epoch=recovery_epoch), sha256).hexdigest()
        raw = {"device_id": device_id, "person_id": person_id, "workspace_id": workspace_id, "issued_at": str(issued), "nonce": value, "body_hash": body_hash, "signature": signature}
        headers = {SESSION_HEADERS[name]: item for name, item in raw.items()}
        if account_id is not None and recovery_epoch is not None:
            headers[ACCOUNT_SESSION_HEADERS["account_id"]] = str(account_id)
            headers[ACCOUNT_SESSION_HEADERS["recovery_epoch"]] = str(recovery_epoch)
        return headers

    @staticmethod
    def message(*, method: str, target: str, body_hash: str, device_id: str, person_id: str, workspace_id: str, issued_at: int, nonce: str, account_id: str | None = None, recovery_epoch: int | None = None) -> bytes:
        if account_id is not None or recovery_epoch is not None:
            if account_id is None or recovery_epoch is None:
                raise ValueError("account_id_and_recovery_epoch_required_together")
            fields = (
                "aion.flow.desktop-session.v2", method.upper(), target, body_hash,
                device_id, person_id, workspace_id, str(account_id),
                str(int(recovery_epoch)), str(issued_at), nonce,
            )
        else:
            fields = (
                "aion.flow.desktop-session.v1", method.upper(), target, body_hash,
                device_id, person_id, workspace_id, str(issued_at), nonce,
            )
        return "\n".join(fields).encode("utf-8")

    def _account_recovery_is_enforced(self) -> bool:
        if self.account_descriptor_registry is not None:
            return True
        if self.enforce_account_recovery is not None:
            if self.enforce_account_recovery and not self.account_recovery_store.state_path.is_file():
                raise RuntimeError("application_account_registry_unavailable")
            return bool(self.enforce_account_recovery)
        return self.account_recovery_store.state_path.is_file()

    def _secret(self) -> bytes:
        if self._explicit_secret is not None:
            if len(self._explicit_secret) < 32:
                raise RuntimeError("aion_flow_session_secret_too_short")
            return self._explicit_secret
        try:
            value = self.key_path.read_bytes()
        except OSError as exc:
            raise RuntimeError("aion_flow_trusted_desktop_not_enrolled") from exc
        if len(value) < 32:
            raise RuntimeError("aion_flow_session_secret_too_short")
        return value

    def _remember_nonce(self, *, device_id: str, nonce: str, issued_at: int, now: int) -> None:
        replay_key = sha256(f"{device_id}\0{nonce}".encode("utf-8")).hexdigest()
        expires_at = issued_at + self.maximum_age_seconds
        if not self.persistent_replay:
            with self._lock:
                self._nonces = {key: expiry for key, expiry in self._nonces.items() if expiry >= now}
                if replay_key in self._nonces:
                    raise PermissionError("signed_aion_flow_session_replayed")
                if len(self._nonces) >= self.maximum_replay_entries:
                    raise PermissionError("signed_aion_flow_session_replay_store_capacity_exceeded")
                self._nonces[replay_key] = expires_at
            return

        path = self.replay_store_path.expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(path.parent, 0o700)
        except OSError:
            pass
        with self._lock:
            try:
                connection = sqlite3.connect(str(path), timeout=5.0, isolation_level=None)
                try:
                    connection.execute("PRAGMA trusted_schema=OFF")
                    connection.execute("PRAGMA journal_mode=WAL")
                    connection.execute("PRAGMA synchronous=FULL")
                    connection.execute(
                        "CREATE TABLE IF NOT EXISTS used_nonces ("
                        "nonce_hash TEXT PRIMARY KEY, expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL)"
                    )
                    connection.execute("BEGIN IMMEDIATE")
                    connection.execute("DELETE FROM used_nonces WHERE expires_at < ?", (now,))
                    count = int(connection.execute("SELECT COUNT(*) FROM used_nonces").fetchone()[0])
                    if count >= self.maximum_replay_entries:
                        connection.execute("ROLLBACK")
                        raise PermissionError("signed_aion_flow_session_replay_store_capacity_exceeded")
                    try:
                        connection.execute(
                            "INSERT INTO used_nonces(nonce_hash, expires_at, created_at) VALUES(?,?,?)",
                            (replay_key, expires_at, now),
                        )
                    except sqlite3.IntegrityError:
                        connection.execute("ROLLBACK")
                        raise PermissionError("signed_aion_flow_session_replayed") from None
                    connection.execute("COMMIT")
                finally:
                    connection.close()
                os.chmod(path, 0o600)
            except PermissionError:
                raise
            except Exception as exc:
                raise RuntimeError("aion_flow_replay_store_unavailable") from exc
