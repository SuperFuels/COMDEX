from __future__ import annotations

import base64
import json
import os
import re
import secrets
import threading
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash
from backend.modules.aion_fabric.identity import DeviceIdentity


_OPAQUE_ID = re.compile(r"^relay_[0-9a-f]{32}$")
_REQUEST_ID = re.compile(r"^relay_request_[0-9a-f]{32}$")


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Relay timestamps require a timezone")
    return parsed.astimezone(timezone.utc)


def _https_endpoint(value: str) -> str:
    clean = str(value or "").strip().rstrip("/")
    parsed = urlparse(clean)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("The relay endpoint must be a trusted HTTPS address")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("The relay endpoint must not contain a path, query, or fragment")
    return clean


def _b64(value: str, *, length: int | None = None, maximum: int | None = None) -> bytes:
    try:
        raw = base64.b64decode(str(value), validate=True)
    except (TypeError, ValueError):
        raise ValueError("The relay envelope contains invalid binary data") from None
    if length is not None and len(raw) != length:
        raise ValueError("The relay envelope contains an invalid key or nonce")
    if maximum is not None and len(raw) > maximum:
        raise ValueError("The relay envelope exceeds its size limit")
    return raw


class OpaqueRelayRouteAuthority:
    """Mother-held cryptography for an operator-unreadable relay route."""

    # The largest direct JSON request contains a base64 voice note. Encrypting
    # that JSON adds another base64 layer, so the opaque transport needs a
    # slightly larger bound than the mother API without relaxing its limits.
    MAX_ENVELOPE_BYTES = 3_000_000
    MAX_VALIDITY_HOURS = 24
    REQUEST_LIFETIME_SECONDS = 120

    def __init__(
        self,
        runtime_dir: str | Path,
        *,
        mother_id: str,
        mother_identity: DeviceIdentity,
        relay_endpoint: str,
    ) -> None:
        self.mother_id = str(mother_id)
        self.identity = mother_identity
        self.relay_endpoint = _https_endpoint(relay_endpoint)
        self.root = Path(runtime_dir) / "pilot_unified" / "opaque_relay"
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        self.key_path = self.root / "transport.key"
        self.route_path = self.root / "route.json"
        self._private_key = self._load_key()
        self._route = self._load_route()

    def _load_key(self) -> X25519PrivateKey:
        if self.key_path.exists():
            raw = self.key_path.read_bytes()
            os.chmod(self.key_path, 0o600)
            if len(raw) != 32:
                raise RuntimeError("The mother relay transport key is invalid")
            return X25519PrivateKey.from_private_bytes(raw)
        key = X25519PrivateKey.generate()
        self.key_path.write_bytes(key.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        ))
        os.chmod(self.key_path, 0o600)
        return key

    def _load_route(self) -> dict[str, str]:
        if self.route_path.exists():
            try:
                record = json.loads(self.route_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raise RuntimeError("The opaque relay route record cannot be verified") from None
            if not _OPAQUE_ID.fullmatch(str(record.get("opaque_route_id") or "")):
                raise RuntimeError("The opaque relay route identifier is invalid")
            if len(str(record.get("submission_token") or "")) < 32:
                raise RuntimeError("The opaque relay submission capability is invalid")
            return record
        record = {
            "opaque_route_id": f"relay_{uuid4().hex}",
            "submission_token": secrets.token_urlsafe(32),
        }
        self.route_path.write_bytes(canonical_bytes(record))
        os.chmod(self.route_path, 0o600)
        return record

    @property
    def opaque_route_id(self) -> str:
        return self._route["opaque_route_id"]

    def descriptor(self, *, validity_hours: int = 24) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        public = self._private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )
        payload = {
            "schema_version": "pilot.opaque-relay-route.v1",
            "mother_id": self.mother_id,
            "mother_fingerprint": self.identity.fingerprint,
            "relay_endpoint": self.relay_endpoint,
            "opaque_route_id": self.opaque_route_id,
            "submission_token": self._route["submission_token"],
            "mother_transport_public_key": base64.b64encode(public).decode("ascii"),
            "transport": "https_tls_1_2_plus",
            "content_encryption": "x25519_hkdf_sha256_aes_256_gcm",
            "operator_can_read_content": False,
            "contains_mother_secret": False,
            "max_envelope_bytes": self.MAX_ENVELOPE_BYTES,
            "request_lifetime_seconds": self.REQUEST_LIFETIME_SECONDS,
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=max(1, min(validity_hours, self.MAX_VALIDITY_HOURS)))).isoformat(),
            "nonce": secrets.token_urlsafe(18),
        }
        hashed = {**payload, "payload_hash": canonical_hash(payload)}
        return {**hashed, "mother_signature": self.identity.sign(canonical_bytes(hashed))}

    @staticmethod
    def verify_descriptor(descriptor: dict[str, Any], mother_public_key: str) -> bool:
        required = {
            "schema_version", "mother_id", "mother_fingerprint", "relay_endpoint",
            "opaque_route_id", "submission_token", "mother_transport_public_key", "transport",
            "content_encryption", "operator_can_read_content", "contains_mother_secret",
            "max_envelope_bytes", "request_lifetime_seconds", "issued_at", "expires_at",
            "nonce", "payload_hash", "mother_signature",
        }
        if set(descriptor) != required or descriptor.get("schema_version") != "pilot.opaque-relay-route.v1":
            return False
        try:
            _https_endpoint(str(descriptor["relay_endpoint"]))
            if not _OPAQUE_ID.fullmatch(str(descriptor["opaque_route_id"])):
                return False
            if len(str(descriptor["submission_token"])) < 32:
                return False
            _b64(str(descriptor["mother_transport_public_key"]), length=32)
            if descriptor.get("transport") != "https_tls_1_2_plus":
                return False
            if descriptor.get("content_encryption") != "x25519_hkdf_sha256_aes_256_gcm":
                return False
            if descriptor.get("operator_can_read_content") is not False or descriptor.get("contains_mother_secret") is not False:
                return False
            if int(descriptor["max_envelope_bytes"]) > OpaqueRelayRouteAuthority.MAX_ENVELOPE_BYTES:
                return False
            if not 1 <= int(descriptor["request_lifetime_seconds"]) <= OpaqueRelayRouteAuthority.REQUEST_LIFETIME_SECONDS:
                return False
            if _time(str(descriptor["expires_at"])) <= datetime.now(timezone.utc):
                return False
            signature = str(descriptor["mother_signature"])
            unsigned = {key: descriptor[key] for key in required if key not in {"payload_hash", "mother_signature"}}
            if not secrets.compare_digest(str(descriptor["payload_hash"]), canonical_hash(unsigned)):
                return False
            signed = {**unsigned, "payload_hash": descriptor["payload_hash"]}
            return DeviceIdentity.verify(mother_public_key, canonical_bytes(signed), signature)
        except (KeyError, TypeError, ValueError):
            return False

    @staticmethod
    def _key(shared: bytes, request_id: str, direction: str) -> bytes:
        return HKDF(
            algorithm=hashes.SHA256(), length=32, salt=None,
            info=canonical_bytes({"protocol": "pilot-opaque-relay-v1", "request_id": request_id, "direction": direction}),
        ).derive(shared)

    def open_request(self, envelope: dict[str, Any]) -> dict[str, Any]:
        metadata_keys = (
            "schema_version", "opaque_route_id", "request_id", "created_at", "expires_at",
            "ephemeral_public_key",
        )
        required = {*metadata_keys, "nonce", "ciphertext"}
        if set(envelope) != required or envelope.get("schema_version") != "pilot.opaque-relay-request.v1":
            raise ValueError("The opaque relay request is malformed")
        if envelope.get("opaque_route_id") != self.opaque_route_id or not _REQUEST_ID.fullmatch(str(envelope.get("request_id") or "")):
            raise PermissionError("The opaque relay request is not addressed to this mother")
        expires = _time(str(envelope["expires_at"]))
        now = datetime.now(timezone.utc)
        if expires <= now or expires > now + timedelta(seconds=self.REQUEST_LIFETIME_SECONDS + 5):
            raise PermissionError("The opaque relay request has expired")
        ephemeral = X25519PublicKey.from_public_bytes(_b64(str(envelope["ephemeral_public_key"]), length=32))
        nonce = _b64(str(envelope["nonce"]), length=12)
        ciphertext = _b64(str(envelope["ciphertext"]), maximum=self.MAX_ENVELOPE_BYTES)
        metadata = {key: envelope[key] for key in metadata_keys}
        shared = self._private_key.exchange(ephemeral)
        raw = AESGCM(self._key(shared, str(envelope["request_id"]), "request")).decrypt(
            nonce, ciphertext, canonical_bytes(metadata),
        )
        value = json.loads(raw)
        if not isinstance(value, dict) or set(value) != {"path", "body"}:
            raise ValueError("The decrypted relay request is malformed")
        path = str(value["path"])
        if not path.startswith("/v1/") or "?" in path or "#" in path or not isinstance(value["body"], dict):
            raise ValueError("The decrypted relay request target is invalid")
        return value

    def seal_response(self, request: dict[str, Any], *, status: int, body: dict[str, Any]) -> dict[str, Any]:
        request_id = str(request["request_id"])
        now = datetime.now(timezone.utc)
        metadata = {
            "schema_version": "pilot.opaque-relay-response.v1",
            "opaque_route_id": self.opaque_route_id,
            "request_id": request_id,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=self.REQUEST_LIFETIME_SECONDS)).isoformat(),
        }
        ephemeral = X25519PublicKey.from_public_bytes(_b64(str(request["ephemeral_public_key"]), length=32))
        shared = self._private_key.exchange(ephemeral)
        nonce = secrets.token_bytes(12)
        ciphertext = AESGCM(self._key(shared, request_id, "response")).encrypt(
            nonce, canonical_bytes({"status": int(status), "body": body}), canonical_bytes(metadata),
        )
        return {
            **metadata,
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }


class OpaqueRelayStore:
    """A bounded reference relay queue that deliberately cannot decrypt payloads."""

    MAX_PENDING_PER_ROUTE = 128
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._routes: dict[str, dict[str, Any]] = {}

    def register(self, descriptor: dict[str, Any], *, poll_token: str) -> None:
        route_id = str(descriptor.get("opaque_route_id") or "")
        if not _OPAQUE_ID.fullmatch(route_id) or len(poll_token) < 32:
            raise ValueError("Relay route registration is invalid")
        with self._lock:
            self._routes[route_id] = {
                "submission_token_hash": canonical_hash(str(descriptor.get("submission_token") or "")),
                "poll_token_hash": canonical_hash(poll_token),
                "requests": deque(), "responses": {}, "seen": set(),
            }

    def submit(self, envelope: dict[str, Any], *, submission_token: str) -> dict[str, Any]:
        route_id = str(envelope.get("opaque_route_id") or "")
        request_id = str(envelope.get("request_id") or "")
        with self._lock:
            route = self._routes.get(route_id)
            if not route or not secrets.compare_digest(route["submission_token_hash"], canonical_hash(submission_token)):
                raise PermissionError("That opaque relay route is unavailable")
            if request_id in route["seen"]:
                return {"accepted": True, "duplicate": True, "request_id": request_id}
            if len(route["requests"]) >= self.MAX_PENDING_PER_ROUTE:
                raise RuntimeError("The opaque relay route is temporarily full")
            # Only transport metadata and ciphertext are retained. The store has no decryption key.
            required = {
                "schema_version", "opaque_route_id", "request_id", "created_at", "expires_at",
                "ephemeral_public_key", "nonce", "ciphertext",
            }
            if set(envelope) != required or envelope.get("schema_version") != "pilot.opaque-relay-request.v1":
                raise ValueError("The opaque relay request is malformed")
            if not _REQUEST_ID.fullmatch(request_id) or _time(str(envelope["expires_at"])) <= datetime.now(timezone.utc):
                raise ValueError("The opaque relay request is invalid or expired")
            _b64(str(envelope["ephemeral_public_key"]), length=32)
            _b64(str(envelope["nonce"]), length=12)
            _b64(str(envelope["ciphertext"]), maximum=OpaqueRelayRouteAuthority.MAX_ENVELOPE_BYTES)
            route["requests"].append(dict(envelope))
            route["seen"].add(request_id)
            return {"accepted": True, "duplicate": False, "request_id": request_id}

    def pull(self, route_id: str, *, poll_token: str) -> dict[str, Any] | None:
        with self._lock:
            route = self._routes.get(route_id)
            if not route or not secrets.compare_digest(route["poll_token_hash"], canonical_hash(poll_token)):
                raise PermissionError("The mother relay poll capability is invalid")
            while route["requests"]:
                request = route["requests"].popleft()
                if _time(str(request["expires_at"])) > datetime.now(timezone.utc):
                    return request
            return None

    def respond(self, response: dict[str, Any], *, poll_token: str) -> None:
        route_id = str(response.get("opaque_route_id") or "")
        request_id = str(response.get("request_id") or "")
        with self._lock:
            route = self._routes.get(route_id)
            if not route or not secrets.compare_digest(route["poll_token_hash"], canonical_hash(poll_token)):
                raise PermissionError("The mother relay poll capability is invalid")
            if request_id not in route["seen"]:
                raise PermissionError("The relay response has no accepted request")
            route["responses"][request_id] = dict(response)

    def receive(self, route_id: str, request_id: str, *, submission_token: str) -> dict[str, Any] | None:
        with self._lock:
            route = self._routes.get(route_id)
            if not route or not secrets.compare_digest(route["submission_token_hash"], canonical_hash(submission_token)):
                raise PermissionError("That opaque relay route is unavailable")
            return route["responses"].pop(request_id, None)

    def operator_view(self, route_id: str) -> dict[str, Any]:
        with self._lock:
            route = self._routes[route_id]
            return {
                "pending_requests": len(route["requests"]),
                "pending_responses": len(route["responses"]),
                "stored_plaintext_fields": [],
                "decryption_keys_held": 0,
            }
