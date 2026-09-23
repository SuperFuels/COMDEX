"""Short-lived, body-bound desktop sessions for AION Flow HTTP operations."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import hmac
import os
from pathlib import Path
import secrets
import threading
import time
from typing import Mapping


SESSION_HEADERS = {
    "device_id": "x-aion-flow-device-id",
    "person_id": "x-aion-flow-person-id",
    "workspace_id": "x-aion-flow-workspace-id",
    "issued_at": "x-aion-flow-issued-at",
    "nonce": "x-aion-flow-nonce",
    "body_hash": "x-aion-flow-body-sha256",
    "signature": "x-aion-flow-signature",
}


@dataclass(frozen=True)
class VerifiedAionFlowSession:
    device_id: str
    person_id: str
    workspace_id: str
    issued_at: int
    nonce: str

    def actor(self) -> dict[str, str]:
        return {
            "person_id": self.person_id,
            "workspace_id": self.workspace_id,
            "organisation_id": self.workspace_id,
            "role": "canonical_authority",
            "authority_source": "signed_desktop_session+canonical_organisation.v1",
        }


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
    ) -> None:
        self.key_path = Path(key_path or os.environ.get("TESSARIS_AION_FLOW_SESSION_KEY_PATH") or Path.home() / ".tessaris/security/aion-flow-desktop-session.key")
        self._explicit_secret = secret
        self.clock = clock
        self.maximum_age_seconds = max(10, min(int(maximum_age_seconds), 300))
        self._nonces: dict[str, int] = {}
        self._lock = threading.Lock()

    def verify(self, *, method: str, target: str, body: bytes, headers: Mapping[str, str]) -> VerifiedAionFlowSession:
        values = {name: str(headers.get(header) or "").strip() for name, header in SESSION_HEADERS.items()}
        if any(not values[name] for name in SESSION_HEADERS):
            raise PermissionError("signed_aion_flow_session_required")
        try:
            issued_at = int(values["issued_at"])
        except ValueError as exc:
            raise PermissionError("signed_aion_flow_session_timestamp_invalid") from exc
        now = int(self.clock())
        if issued_at > now + 5 or now - issued_at > self.maximum_age_seconds:
            raise PermissionError("signed_aion_flow_session_expired")
        if len(values["nonce"]) < 16 or len(values["nonce"]) > 128:
            raise PermissionError("signed_aion_flow_session_nonce_invalid")
        actual_body_hash = sha256(body).hexdigest()
        if not hmac.compare_digest(actual_body_hash, values["body_hash"]):
            raise PermissionError("signed_aion_flow_session_body_changed")
        message = self.message(
            method=method,
            target=target,
            body_hash=values["body_hash"],
            device_id=values["device_id"],
            person_id=values["person_id"],
            workspace_id=values["workspace_id"],
            issued_at=issued_at,
            nonce=values["nonce"],
        )
        expected = hmac.new(self._secret(), message, sha256).hexdigest()
        if not hmac.compare_digest(expected, values["signature"]):
            raise PermissionError("signed_aion_flow_session_invalid")
        with self._lock:
            self._nonces = {key: expiry for key, expiry in self._nonces.items() if expiry >= now}
            replay_key = f"{values['device_id']}:{values['nonce']}"
            if replay_key in self._nonces:
                raise PermissionError("signed_aion_flow_session_replayed")
            self._nonces[replay_key] = issued_at + self.maximum_age_seconds
        return VerifiedAionFlowSession(
            device_id=values["device_id"], person_id=values["person_id"],
            workspace_id=values["workspace_id"], issued_at=issued_at, nonce=values["nonce"],
        )

    def sign_for_test(self, *, method: str, target: str, body: bytes, device_id: str, person_id: str, workspace_id: str, issued_at: int | None = None, nonce: str | None = None) -> dict[str, str]:
        issued = int(self.clock()) if issued_at is None else int(issued_at)
        value = nonce or secrets.token_hex(16)
        body_hash = sha256(body).hexdigest()
        signature = hmac.new(self._secret(), self.message(method=method, target=target, body_hash=body_hash, device_id=device_id, person_id=person_id, workspace_id=workspace_id, issued_at=issued, nonce=value), sha256).hexdigest()
        raw = {"device_id": device_id, "person_id": person_id, "workspace_id": workspace_id, "issued_at": str(issued), "nonce": value, "body_hash": body_hash, "signature": signature}
        return {SESSION_HEADERS[name]: item for name, item in raw.items()}

    @staticmethod
    def message(*, method: str, target: str, body_hash: str, device_id: str, person_id: str, workspace_id: str, issued_at: int, nonce: str) -> bytes:
        return "\n".join(("aion.flow.desktop-session.v1", method.upper(), target, body_hash, device_id, person_id, workspace_id, str(issued_at), nonce)).encode("utf-8")

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
