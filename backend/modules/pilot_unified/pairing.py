from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse
from uuid import uuid4

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash, utc_now_iso
from backend.modules.aion_fabric.identity import DeviceIdentity
from backend.modules.aion_fabric.private_identity import ProductionPrivateIdentity

from .opaque_relay import OpaqueRelayRouteAuthority


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@/-]{0,199}$")
_SCOPE = re.compile(r"^[a-z0-9][a-z0-9_.:-]{1,99}$")
_TRUST_WORDS = (
    "amber", "anchor", "apple", "arrow", "atlas", "birch", "blue", "cedar",
    "cloud", "coral", "dawn", "delta", "eagle", "ember", "falcon", "fern",
    "field", "fjord", "forest", "frost", "gold", "harbor", "hazel", "island",
    "jade", "lake", "leaf", "light", "lunar", "maple", "meadow", "mist",
    "north", "oak", "ocean", "olive", "orchid", "pearl", "pine", "quartz",
    "rain", "reef", "river", "sage", "sand", "silver", "sky", "snow",
    "solar", "south", "spring", "star", "stone", "sun", "tide", "valley",
    "violet", "wave", "west", "willow", "wind", "winter", "wood", "zenith",
)


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("A pairing timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def _public_key(value: str) -> str:
    try:
        raw = base64.b64decode(str(value), validate=True)
    except (TypeError, ValueError):
        raise ValueError("The phone public key is invalid") from None
    if len(raw) != 32:
        raise ValueError("The phone public key must be Ed25519")
    return str(value)


def _identifier(value: str, label: str) -> str:
    clean = str(value or "").strip()
    if not _IDENTIFIER.fullmatch(clean):
        raise ValueError(f"{label} is invalid")
    return clean


def _endpoint(value: str) -> str:
    clean = str(value or "").strip().rstrip("/")
    parsed = urlparse(clean)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("The mother endpoint must be a trusted HTTPS address")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("The mother endpoint must not contain a path, query, or fragment")
    return clean


class MobilePairingAuthority:
    """Persistent phone-to-mother trust with single-use challenges and leases."""

    _lock = threading.RLock()
    MAX_ATTEMPTS = 5
    MAX_LEASE_HOURS = 24
    # The unified app now has separately reviewable Personal, Workspace and
    # Boardroom capabilities. Keep a firm ceiling while allowing least-privilege
    # scopes instead of collapsing them into one overbroad mobile permission.
    MAX_SCOPES = 96

    def __init__(
        self,
        runtime_dir: str | Path,
        *,
        mother_id: str,
        mother_identity: DeviceIdentity,
        endpoint: str,
        ca_sha256: str,
        ca_certificate_pem: bytes | str | None = None,
        identity_registry: ProductionPrivateIdentity,
        remote_endpoints: Iterable[str] = (),
        relay_endpoint: str | None = None,
    ) -> None:
        self.mother_id = _identifier(mother_id, "mother_id")
        self.identity = mother_identity
        self.endpoint = _endpoint(endpoint)
        self.ca_sha256 = str(ca_sha256).lower()
        certificate = ca_certificate_pem.encode("utf-8") if isinstance(ca_certificate_pem, str) else ca_certificate_pem
        self.ca_certificate_pem = bytes(certificate or b"")
        self.identity_registry = identity_registry
        cleaned_remote = []
        for candidate in remote_endpoints:
            endpoint_candidate = _endpoint(str(candidate))
            if endpoint_candidate != self.endpoint and endpoint_candidate not in cleaned_remote:
                cleaned_remote.append(endpoint_candidate)
        if len(cleaned_remote) > 4:
            raise ValueError("Pilot supports at most four direct remote endpoints")
        self.remote_endpoints = tuple(cleaned_remote)
        self.opaque_relay = OpaqueRelayRouteAuthority(
            runtime_dir,
            mother_id=self.mother_id,
            mother_identity=self.identity,
            relay_endpoint=relay_endpoint,
        ) if relay_endpoint else None
        if not re.fullmatch(r"[0-9a-f]{64}", self.ca_sha256):
            raise ValueError("The household certificate fingerprint must be SHA-256")
        if self.ca_certificate_pem:
            try:
                from cryptography import x509
                from cryptography.hazmat.primitives import hashes
                parsed_certificate = x509.load_pem_x509_certificate(self.ca_certificate_pem)
                actual_fingerprint = parsed_certificate.fingerprint(hashes.SHA256()).hex()
            except ValueError as exc:
                raise ValueError("The household certificate must be a valid PEM certificate") from exc
            if not secrets.compare_digest(actual_fingerprint, self.ca_sha256):
                raise ValueError("The household certificate does not match its fingerprint")
        self.path = Path(runtime_dir) / "pilot_unified" / "mobile_pairing.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)

    def _initial(self) -> dict[str, Any]:
        return {
            "schema_version": "pilot.mobile-pairing.v1",
            "mother_id": self.mother_id,
            "mother_public_key": self.identity.public_key_b64,
            "mother_fingerprint": self.identity.fingerprint,
            "challenges": [],
            "devices": [],
            "leases": [],
            "used_nonces": [],
            "revocations": [],
        }

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._initial()
        try:
            state = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise RuntimeError("Pilot cannot safely read the phone trust store") from None
        if (
            not isinstance(state, dict)
            or state.get("mother_id") != self.mother_id
            or state.get("mother_public_key") != self.identity.public_key_b64
        ):
            raise PermissionError("The phone trust store belongs to a different mother identity")
        return state

    def _write(self, state: dict[str, Any]) -> None:
        state["updated_at"] = utc_now_iso()
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)
        os.chmod(self.path, 0o600)

    def mother_descriptor(self, *, validity_minutes: int = 10) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        payload = {
            "schema_version": "pilot.mother-descriptor.v2" if self.ca_certificate_pem else "pilot.mother-descriptor.v1",
            "mother_id": self.mother_id,
            "mother_public_key": self.identity.public_key_b64,
            "mother_fingerprint": self.identity.fingerprint,
            "endpoint": self.endpoint,
            "ca_sha256": self.ca_sha256,
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=max(1, min(validity_minutes, 30)))).isoformat(),
        }
        if self.ca_certificate_pem:
            # Public trust anchor only. This is signed with the Node identity;
            # it contains no private key and lets a newly paired phone pin the
            # Node's self-managed TLS CA without a global trust installation.
            payload["ca_certificate_pem_b64"] = base64.b64encode(self.ca_certificate_pem).decode("ascii")
        return {**payload, "mother_signature": self.identity.sign(canonical_bytes(payload))}

    def pairing_invitation(
        self,
        *,
        persona_id: str,
        requested_scopes: Iterable[str] = ("message.send", "task.create", "tv.control"),
        validity_minutes: int = 10,
    ) -> dict[str, Any]:
        """Create the public, QR-safe start of a phone pairing journey.

        An invitation deliberately contains no confirmation code, certificate,
        lease, relay capability or mother secret.  The phone still creates its
        own key, requests a single-use challenge, and needs the exact local
        confirmation presented by the trusted Node before it is enrolled.
        """
        persona_id = _identifier(persona_id, "persona_id")
        scopes = sorted(set(str(scope) for scope in requested_scopes))
        if not scopes or len(scopes) > self.MAX_SCOPES or any(not _SCOPE.fullmatch(scope) for scope in scopes):
            raise ValueError("The requested phone permissions are invalid")
        now = datetime.now(timezone.utc)
        descriptor = self.mother_descriptor(validity_minutes=validity_minutes)
        payload = {
            "schema_version": "pilot.phone-pairing-invitation.v1",
            "mother_descriptor": descriptor,
            "persona_id": persona_id,
            "requested_scopes": scopes,
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=max(1, min(validity_minutes, 30)))).isoformat(),
            "nonce": secrets.token_urlsafe(18),
            "contains_mother_secret": False,
            "contains_pairing_confirmation": False,
        }
        return self._signed(payload)

    @staticmethod
    def verify_pairing_invitation(invitation: dict[str, Any]) -> bool:
        """Reject altered, expired or over-broad QR invitation payloads."""
        required = {
            "schema_version", "mother_descriptor", "persona_id", "requested_scopes",
            "issued_at", "expires_at", "nonce", "contains_mother_secret",
            "contains_pairing_confirmation", "payload_hash", "mother_signature",
        }
        if set(invitation) != required or invitation.get("schema_version") != "pilot.phone-pairing-invitation.v1":
            return False
        try:
            descriptor = invitation["mother_descriptor"]
            if not isinstance(descriptor, dict) or not MobilePairingAuthority.verify_mother_descriptor(descriptor):
                return False
            if _parse_time(str(invitation["expires_at"])) <= datetime.now(timezone.utc):
                return False
            if _parse_time(str(descriptor["expires_at"])) < _parse_time(str(invitation["expires_at"])):
                return False
            _identifier(str(invitation["persona_id"]), "persona_id")
            scopes = list(invitation["requested_scopes"])
            if not scopes or len(scopes) > MobilePairingAuthority.MAX_SCOPES or scopes != sorted(set(scopes)):
                return False
            if any(not _SCOPE.fullmatch(str(scope)) for scope in scopes):
                return False
            if invitation.get("contains_mother_secret") is not False or invitation.get("contains_pairing_confirmation") is not False:
                return False
            payload = {key: invitation[key] for key in required if key not in {"payload_hash", "mother_signature"}}
            if not secrets.compare_digest(str(invitation["payload_hash"]), canonical_hash(payload)):
                return False
            signed = {**payload, "payload_hash": invitation["payload_hash"]}
            return DeviceIdentity.verify(
                str(descriptor["mother_public_key"]),
                canonical_bytes(signed),
                str(invitation["mother_signature"]),
            )
        except (KeyError, TypeError, ValueError):
            return False

    def direct_remote_route(self, *, validity_hours: int = 24) -> dict[str, Any] | None:
        """Return a phone-cacheable direct route without a relay or mother secret."""
        if not self.remote_endpoints:
            return None
        now = datetime.now(timezone.utc)
        payload = {
            "schema_version": "pilot.direct-remote-route.v1",
            "mother_id": self.mother_id,
            "mother_fingerprint": self.identity.fingerprint,
            "endpoints": list(self.remote_endpoints),
            "transport": "https_tls_1_2_plus",
            "application_authentication": "signed_phone_possession",
            "relay_used": False,
            "contains_mother_secret": False,
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=max(1, min(validity_hours, 72)))).isoformat(),
            "nonce": secrets.token_urlsafe(18),
        }
        return self._signed(payload)

    def opaque_relay_route(self, *, validity_hours: int = 24) -> dict[str, Any] | None:
        return self.opaque_relay.descriptor(validity_hours=validity_hours) if self.opaque_relay else None

    @staticmethod
    def verify_direct_remote_route(route: dict[str, Any], mother_public_key: str) -> bool:
        required = {
            "schema_version", "mother_id", "mother_fingerprint", "endpoints", "transport",
            "application_authentication", "relay_used", "contains_mother_secret", "issued_at",
            "expires_at", "nonce", "payload_hash", "mother_signature",
        }
        if set(route) != required or route.get("schema_version") != "pilot.direct-remote-route.v1":
            return False
        try:
            endpoints = list(route["endpoints"])
            if not endpoints or len(endpoints) > 4 or endpoints != list(dict.fromkeys(endpoints)):
                return False
            for endpoint in endpoints:
                _endpoint(str(endpoint))
            if route.get("relay_used") is not False or route.get("contains_mother_secret") is not False:
                return False
            if route.get("transport") != "https_tls_1_2_plus" or route.get("application_authentication") != "signed_phone_possession":
                return False
            if _parse_time(str(route["expires_at"])) <= datetime.now(timezone.utc):
                return False
            signature = str(route["mother_signature"])
            payload = {key: route[key] for key in required if key not in {"mother_signature", "payload_hash"}}
            if not secrets.compare_digest(str(route["payload_hash"]), canonical_hash(payload)):
                return False
            signed = {**payload, "payload_hash": route["payload_hash"]}
            return DeviceIdentity.verify(mother_public_key, canonical_bytes(signed), signature)
        except (KeyError, TypeError, ValueError):
            return False

    def trust_words(self) -> list[str]:
        raw = bytes.fromhex(hashlib.sha256(self.identity.public_key_bytes).hexdigest())
        return [_TRUST_WORDS[value & 63] for value in raw[:6]]

    @staticmethod
    def verify_mother_descriptor(descriptor: dict[str, Any], *, expected_fingerprint: str | None = None) -> bool:
        required_v1 = {
            "schema_version", "mother_id", "mother_public_key", "mother_fingerprint",
            "endpoint", "ca_sha256", "issued_at", "expires_at", "mother_signature",
        }
        required_v2 = required_v1 | {"ca_certificate_pem_b64"}
        version = descriptor.get("schema_version")
        if (version == "pilot.mother-descriptor.v1" and set(descriptor) != required_v1) or (
            version == "pilot.mother-descriptor.v2" and set(descriptor) != required_v2
        ) or version not in {"pilot.mother-descriptor.v1", "pilot.mother-descriptor.v2"}:
            return False
        try:
            public_key = _public_key(str(descriptor["mother_public_key"]))
            calculated = hashlib.sha256(base64.b64decode(public_key)).hexdigest()[:32]
            _endpoint(str(descriptor["endpoint"]))
            if calculated != descriptor["mother_fingerprint"]:
                return False
            if expected_fingerprint and not secrets.compare_digest(calculated, str(expected_fingerprint)):
                return False
            if _parse_time(str(descriptor["expires_at"])) <= datetime.now(timezone.utc):
                return False
            if version == "pilot.mother-descriptor.v2":
                from cryptography import x509
                from cryptography.hazmat.primitives import hashes
                certificate = x509.load_pem_x509_certificate(base64.b64decode(str(descriptor["ca_certificate_pem_b64"]), validate=True))
                if not secrets.compare_digest(certificate.fingerprint(hashes.SHA256()).hex(), str(descriptor["ca_sha256"])):
                    return False
            required = required_v2 if version == "pilot.mother-descriptor.v2" else required_v1
            payload = {key: descriptor[key] for key in required if key != "mother_signature"}
            return DeviceIdentity.verify(public_key, canonical_bytes(payload), str(descriptor["mother_signature"]))
        except (KeyError, TypeError, ValueError):
            return False

    def begin_pairing(
        self,
        *,
        persona_id: str,
        device_label: str,
        phone_public_key: str,
        requested_scopes: Iterable[str] = ("message.send", "task.create", "tv.control"),
    ) -> dict[str, Any]:
        persona_id = _identifier(persona_id, "persona_id")
        phone_public_key = _public_key(phone_public_key)
        label = " ".join(str(device_label).split())[:80]
        if len(label) < 2:
            raise ValueError("Give this phone a recognizable name")
        scopes = sorted(set(str(scope) for scope in requested_scopes))
        if not scopes or len(scopes) > self.MAX_SCOPES or any(not _SCOPE.fullmatch(scope) for scope in scopes):
            raise ValueError("The requested phone permissions are invalid")
        now = datetime.now(timezone.utc)
        descriptor = self.mother_descriptor()
        with self._lock:
            state = self._read()
            pending = [
                item for item in state.get("challenges", [])
                if item.get("status") == "pending" and _parse_time(str(item["expires_at"])) > now
            ]
            for item in pending:
                if item.get("persona_id") == persona_id and item.get("phone_public_key") == phone_public_key:
                    item["status"] = "superseded"
            code = f"{secrets.randbelow(1_000_000):06d}"
            challenge_id = f"pair_{uuid4().hex}"
            challenge = {
                "schema_version": "pilot.phone-pairing-challenge.v1",
                "challenge_id": challenge_id,
                "mother_id": self.mother_id,
                "mother_fingerprint": self.identity.fingerprint,
                "mother_descriptor_hash": canonical_hash(descriptor),
                "persona_id": persona_id,
                "device_id": f"phone_{uuid4().hex}",
                "device_label": label,
                "phone_public_key": phone_public_key,
                "requested_scopes": scopes,
                "nonce": secrets.token_urlsafe(24),
                "issued_at": now.isoformat(),
                "expires_at": (now + timedelta(minutes=5)).isoformat(),
                "attempts": 0,
                "status": "pending",
                "code_hash": canonical_hash({"challenge_id": challenge_id, "code": code, "mother_fingerprint": self.identity.fingerprint}),
            }
            state["challenges"] = (pending + [challenge])[-32:]
            self._write(state)
        signed_fields = self._challenge_payload(challenge)
        return {
            "phone_challenge": {
                **signed_fields,
                "mother_descriptor": descriptor,
                "mother_signature": self.identity.sign(canonical_bytes(signed_fields)),
            },
            "local_confirmation": {
                "challenge_id": challenge_id,
                "confirmation_code": code,
                "device_label": label,
                "trust_words": self.trust_words(),
                "expires_at": challenge["expires_at"],
            },
        }

    @staticmethod
    def _challenge_payload(challenge: dict[str, Any]) -> dict[str, Any]:
        fields = (
            "schema_version", "challenge_id", "mother_id", "mother_fingerprint",
            "mother_descriptor_hash", "persona_id", "device_id", "device_label",
            "requested_scopes", "nonce", "issued_at", "expires_at",
        )
        return {key: challenge[key] for key in fields}

    def _signed(self, payload: dict[str, Any]) -> dict[str, Any]:
        with_hash = {**payload, "payload_hash": canonical_hash(payload)}
        return {**with_hash, "mother_signature": self.identity.sign(canonical_bytes(with_hash))}

    def _issue_lease(
        self,
        *,
        device: dict[str, Any],
        scopes: list[str],
        hours: int = 8,
        previous_lease_id: str | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        return self._signed({
            "schema_version": "pilot.mobile-lease.v1",
            "lease_id": f"mobile_lease_{uuid4().hex}",
            "certificate_id": device["certificate_id"],
            "device_id": device["device_id"],
            "persona_id": device["persona_id"],
            "mother_id": self.mother_id,
            "scopes": scopes,
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=max(1, min(hours, self.MAX_LEASE_HOURS)))).isoformat(),
            "previous_lease_id": previous_lease_id,
            "status": "active",
        })

    def complete_pairing(self, *, challenge_id: str, confirmation_code: str, phone_signature: str) -> dict[str, Any]:
        challenge_id = _identifier(challenge_id, "challenge_id")
        with self._lock:
            state = self._read()
            challenge = next((item for item in state.get("challenges", []) if item.get("challenge_id") == challenge_id), None)
            if challenge is None:
                raise KeyError("That pairing request is no longer available")
            if challenge.get("status") != "pending":
                raise PermissionError("That pairing request has already been used")
            if _parse_time(str(challenge["expires_at"])) <= datetime.now(timezone.utc):
                challenge["status"] = "expired"
                self._write(state)
                raise PermissionError("That pairing code has expired; show a new one")
            expected = canonical_hash({
                "challenge_id": challenge_id,
                "code": str(confirmation_code),
                "mother_fingerprint": self.identity.fingerprint,
            })
            if not secrets.compare_digest(str(challenge["code_hash"]), expected):
                challenge["attempts"] = int(challenge.get("attempts") or 0) + 1
                if challenge["attempts"] >= self.MAX_ATTEMPTS:
                    challenge["status"] = "locked"
                self._write(state)
                raise PermissionError("That pairing code does not match")
            signed = self._challenge_payload(challenge)
            if not DeviceIdentity.verify(str(challenge["phone_public_key"]), canonical_bytes(signed), phone_signature):
                raise PermissionError("This phone did not prove possession of its key")
            self.identity_registry.enroll_phone_from_verified_pairing(
                persona_id=str(challenge["persona_id"]),
                device_id=str(challenge["device_id"]),
                device_label=str(challenge["device_label"]),
                public_key=str(challenge["phone_public_key"]),
                pairing_payload=signed,
                signature=phone_signature,
                mother_id=self.mother_id,
            )
            now = datetime.now(timezone.utc)
            certificate = self._signed({
                "schema_version": "pilot.phone-certificate.v1",
                "certificate_id": f"phone_cert_{uuid4().hex}",
                "device_id": challenge["device_id"],
                "persona_id": challenge["persona_id"],
                "device_label": challenge["device_label"],
                "phone_public_key": challenge["phone_public_key"],
                "mother_id": self.mother_id,
                "mother_fingerprint": self.identity.fingerprint,
                "ca_sha256": self.ca_sha256,
                "issued_at": now.isoformat(),
                "expires_at": (now + timedelta(days=397)).isoformat(),
                "status": "trusted",
            })
            device = dict(certificate)
            lease = self._issue_lease(device=device, scopes=list(challenge["requested_scopes"]))
            challenge["status"] = "consumed"
            challenge["consumed_at"] = utc_now_iso()
            state["devices"] = [item for item in state.get("devices", []) if item.get("device_id") != device["device_id"]] + [device]
            state["leases"] = list(state.get("leases", []))[-127:] + [lease]
            self._write(state)
            return {
                "certificate": certificate,
                "lease": lease,
                "connection": self.connection_state(device_id=device["device_id"], state=state),
                "direct_remote_route": self.direct_remote_route(),
                "opaque_relay_route": self.opaque_relay_route(),
            }

    def _verify_mother_signed(self, record: dict[str, Any]) -> bool:
        signature = str(record.get("mother_signature") or "")
        payload = {key: value for key, value in record.items() if key != "mother_signature"}
        expected_hash = payload.pop("payload_hash", "")
        if not secrets.compare_digest(str(expected_hash), canonical_hash(payload)):
            return False
        payload["payload_hash"] = expected_hash
        return DeviceIdentity.verify(self.identity.public_key_b64, canonical_bytes(payload), signature)

    def renew_lease(self, request: dict[str, Any], *, phone_signature: str) -> dict[str, Any]:
        required = {"purpose", "device_id", "persona_id", "previous_lease_id", "requested_scopes", "nonce"}
        if set(request) != required or request.get("purpose") != "renew_mobile_lease":
            raise ValueError("The lease renewal request is malformed")
        nonce = _identifier(str(request["nonce"]), "nonce")
        scopes = sorted(set(str(scope) for scope in request.get("requested_scopes", [])))
        if scopes != request.get("requested_scopes") or any(not _SCOPE.fullmatch(scope) for scope in scopes):
            raise ValueError("Lease permissions must be unique and ordered")
        with self._lock:
            state = self._read()
            if nonce in state.get("used_nonces", []):
                raise PermissionError("That connection renewal has already been used")
            device = next((item for item in state.get("devices", []) if item.get("device_id") == request["device_id"]), None)
            if not device or device.get("status") != "trusted" or device.get("persona_id") != request["persona_id"]:
                raise PermissionError("This phone is no longer trusted")
            authoritative = self.identity_registry.device_status(
                persona_id=str(request["persona_id"]),
                device_id=str(request["device_id"]),
            )
            if authoritative.get("status") != "trusted" or not authoritative.get("possession_verified"):
                raise PermissionError("This phone is no longer trusted")
            previous = next((item for item in state.get("leases", []) if item.get("lease_id") == request["previous_lease_id"]), None)
            if not previous or previous.get("device_id") != device["device_id"] or previous.get("status") not in {"active", "expired"}:
                raise PermissionError("The previous connection lease is invalid")
            if not set(scopes).issubset(set(previous.get("scopes") or [])):
                raise PermissionError("Reconnect cannot silently add permissions")
            if not DeviceIdentity.verify(str(device["phone_public_key"]), canonical_bytes(request), phone_signature):
                raise PermissionError("This phone did not sign the reconnect request")
            state["used_nonces"] = list(state.get("used_nonces", []))[-255:] + [nonce]
            previous["status"] = "rotated"
            lease = self._issue_lease(device=device, scopes=scopes, previous_lease_id=str(previous["lease_id"]))
            state["leases"] = list(state.get("leases", []))[-127:] + [lease]
            self._write(state)
            return lease

    def validate(self, *, certificate: dict[str, Any], lease: dict[str, Any], required_scope: str) -> dict[str, Any]:
        if not self._verify_mother_signed(certificate) or not self._verify_mother_signed(lease):
            raise PermissionError("Pilot could not verify the phone connection")
        now = datetime.now(timezone.utc)
        if _parse_time(str(certificate["expires_at"])) <= now or _parse_time(str(lease["expires_at"])) <= now:
            raise PermissionError("The phone connection has expired")
        with self._lock:
            state = self._read()
            device = next((item for item in state.get("devices", []) if item.get("device_id") == certificate.get("device_id")), None)
            stored_lease = next((item for item in state.get("leases", []) if item.get("lease_id") == lease.get("lease_id")), None)
            if not device or device.get("status") != "trusted" or not stored_lease or stored_lease.get("status") != "active":
                raise PermissionError("This phone is no longer trusted")
            authoritative = self.identity_registry.device_status(
                persona_id=str(certificate.get("persona_id") or ""),
                device_id=str(certificate.get("device_id") or ""),
            )
            if authoritative.get("status") != "trusted" or not authoritative.get("possession_verified"):
                raise PermissionError("This phone is no longer trusted")
            if lease.get("certificate_id") != certificate.get("certificate_id") or lease.get("device_id") != certificate.get("device_id"):
                raise PermissionError("The phone certificate and connection do not match")
            if required_scope not in lease.get("scopes", []):
                raise PermissionError("This phone is not allowed to do that")
        return {"valid": True, "device_id": certificate["device_id"], "persona_id": certificate["persona_id"], "scope": required_scope}

    def validate_signed_request(
        self,
        *,
        certificate: dict[str, Any],
        lease: dict[str, Any],
        required_scope: str,
        request: dict[str, Any],
        phone_signature: str,
    ) -> dict[str, Any]:
        authority = self.validate(certificate=certificate, lease=lease, required_scope=required_scope)
        if str(request.get("persona_id") or "") != str(authority["persona_id"]):
            raise PermissionError("This request belongs to a different private identity")
        if not DeviceIdentity.verify(
            str(certificate.get("phone_public_key") or ""),
            canonical_bytes(request),
            phone_signature,
        ):
            raise PermissionError("This phone did not sign the Personal Pilot request")
        return authority

    def revoke_device(self, *, device_id: str, reason: str = "owner_requested") -> dict[str, Any]:
        device_id = _identifier(device_id, "device_id")
        with self._lock:
            state = self._read()
            device = next((item for item in state.get("devices", []) if item.get("device_id") == device_id), None)
            if device is None:
                raise KeyError("That phone is not registered")
            self.identity_registry.revoke_device(
                persona_id=str(device["persona_id"]),
                device_id=device_id,
                reason=reason,
            )
            device["status"] = "revoked"
            device["revoked_at"] = utc_now_iso()
            device["revocation_reason"] = " ".join(str(reason).split())[:120] or "owner_requested"
            revoked_leases = 0
            for lease in state.get("leases", []):
                if lease.get("device_id") == device_id and lease.get("status") == "active":
                    lease["status"] = "revoked"
                    lease["revoked_at"] = utc_now_iso()
                    revoked_leases += 1
            state["revocations"] = list(state.get("revocations", []))[-127:] + [{
                "device_id": device_id,
                "reason": device["revocation_reason"],
                "revoked_at": device["revoked_at"],
                "leases_revoked": revoked_leases,
            }]
            self._write(state)
            return {"device_id": device_id, "status": "revoked", "leases_revoked": revoked_leases, "shared_screen_authority_revoked": True}

    def connection_state(self, *, device_id: str, state: dict[str, Any] | None = None) -> dict[str, Any]:
        state = state or self._read()
        device = next((item for item in state.get("devices", []) if item.get("device_id") == device_id), None)
        if not device:
            return {"state": "not_connected", "message": "This phone has not been connected to Pilot."}
        if device.get("status") == "revoked":
            return {"state": "revoked", "message": "This phone was removed. Connect it again only if you trust it."}
        authoritative = self.identity_registry.device_status(
            persona_id=str(device["persona_id"]),
            device_id=str(device["device_id"]),
        )
        if authoritative.get("status") != "trusted":
            return {"state": "revoked", "message": "This phone was removed. Connect it again only if you trust it."}
        leases = [item for item in state.get("leases", []) if item.get("device_id") == device_id and item.get("status") == "active"]
        live = [item for item in leases if _parse_time(str(item["expires_at"])) > datetime.now(timezone.utc)]
        if live:
            return {"state": "connected", "message": "Connected securely to your Pilot.", "mother_name": self.mother_id, "direct_at_home": True}
        return {"state": "needs_reconnect", "message": "Pilot found your phone, but the secure connection needs renewing."}

    def inventory(self) -> dict[str, Any]:
        state = self._read()
        devices = []
        for item in state.get("devices", []):
            devices.append({
                "device_id": item.get("device_id"),
                "persona_id": item.get("persona_id"),
                "device_label": item.get("device_label"),
                "status": item.get("status"),
                "issued_at": item.get("issued_at"),
                "revoked_at": item.get("revoked_at"),
            })
        return {"mother_id": self.mother_id, "devices": devices, "count": len(devices)}
