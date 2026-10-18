from __future__ import annotations

import base64
import json
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from backend.modules.aion_fabric.canonical import canonical_bytes
from backend.modules.aion_fabric.identity import DeviceIdentity
from backend.modules.aion_fabric.local_tls import LocalTLSAuthority
from backend.modules.pilot_unified.opaque_relay import OpaqueRelayRouteAuthority
from backend.modules.pilot_unified.self_hosted_relay import SelfHostedOpaqueRelayService


def _post(url: str, value: dict, context: ssl.SSLContext) -> dict:
    request = urllib.request.Request(
        url, data=json.dumps(value).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(request, context=context, timeout=3) as response:
        assert response.headers["Strict-Transport-Security"] == "max-age=31536000"
        return json.loads(response.read())


def _key(shared: bytes, request_id: str, direction: str) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None,
        info=canonical_bytes({"protocol": "pilot-opaque-relay-v1", "request_id": request_id, "direction": direction}),
    ).derive(shared)


def test_self_hosted_tls_relay_round_trip_remains_operator_unreadable(tmp_path):
    material = LocalTLSAuthority(tmp_path / "tls-runtime").ensure(address="127.0.0.1", hostname="relay-test.local")
    service = SelfHostedOpaqueRelayService(tls_context=material.context(), port=0)
    service.start()
    try:
        context = ssl.create_default_context(cafile=str(material.ca_certificate_path))
        base = f"https://127.0.0.1:{service.port_in_use}"
        with urllib.request.urlopen(f"{base}/health", context=context, timeout=3) as response:
            health = json.loads(response.read())
        assert health["operator_can_read_content"] is False
        assert health["decryption_keys_held"] == 0

        identity = DeviceIdentity(Ed25519PrivateKey.generate())
        authority = OpaqueRelayRouteAuthority(
            tmp_path / "mother", mother_id="mother_customer", mother_identity=identity,
            relay_endpoint=base,
        )
        descriptor = authority.descriptor()
        poll_token = "customer-owned-mother-poll-token-123456"
        registered = _post(f"{base}/v1/routes/register", {
            "descriptor": descriptor, "mother_public_key": identity.public_key_b64,
            "poll_token": poll_token,
        }, context)
        assert registered["registered"] is True

        request_id = "relay_request_" + "a" * 32
        ephemeral = X25519PrivateKey.generate()
        mother_public = X25519PublicKey.from_public_bytes(base64.b64decode(descriptor["mother_transport_public_key"]))
        shared = ephemeral.exchange(mother_public)
        now = datetime.now(timezone.utc)
        metadata = {
            "schema_version": "pilot.opaque-relay-request.v1",
            "opaque_route_id": descriptor["opaque_route_id"], "request_id": request_id,
            "created_at": now.isoformat(), "expires_at": (now + timedelta(seconds=60)).isoformat(),
            "ephemeral_public_key": base64.b64encode(ephemeral.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw,
            )).decode("ascii"),
        }
        private_request = {"path": "/v1/personal/snapshot", "body": {"private": "customer secret"}}
        nonce = b"n" * 12
        envelope = {
            **metadata, "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(AESGCM(_key(shared, request_id, "request")).encrypt(
                nonce, canonical_bytes(private_request), canonical_bytes(metadata),
            )).decode("ascii"),
        }
        assert "customer secret" not in json.dumps(envelope)
        submitted = _post(f"{base}/v1/requests/submit", {
            "envelope": envelope, "submission_token": descriptor["submission_token"],
        }, context)
        assert submitted["accepted"] is True

        pulled = _post(f"{base}/v1/requests/pull", {
            "opaque_route_id": descriptor["opaque_route_id"], "poll_token": poll_token,
        }, context)["envelope"]
        assert authority.open_request(pulled) == private_request
        response = authority.seal_response(pulled, status=200, body={"private": "customer result"})
        _post(f"{base}/v1/responses/submit", {"response": response, "poll_token": poll_token}, context)
        delivered = _post(f"{base}/v1/responses/receive", {
            "opaque_route_id": descriptor["opaque_route_id"], "request_id": request_id,
            "submission_token": descriptor["submission_token"],
        }, context)["response"]
        assert "customer result" not in json.dumps(delivered)
        status = _post(f"{base}/v1/operator/status", {
            "opaque_route_id": descriptor["opaque_route_id"],
        }, context)
        assert status["stored_plaintext_fields"] == []
        assert status["decryption_keys_held"] == 0

        with urllib.request.urlopen(f"{base}/health", context=context, timeout=3) as response:
            assert response.status == 200
    finally:
        service.stop()


def test_self_hosted_relay_rejects_unsigned_route_registration(tmp_path):
    material = LocalTLSAuthority(tmp_path / "tls-runtime").ensure(address="127.0.0.1", hostname="relay-test.local")
    service = SelfHostedOpaqueRelayService(tls_context=material.context(), port=0)
    service.start()
    try:
        context = ssl.create_default_context(cafile=str(material.ca_certificate_path))
        base = f"https://127.0.0.1:{service.port_in_use}"
        request = urllib.request.Request(
            f"{base}/v1/routes/register",
            data=json.dumps({"descriptor": {}, "mother_public_key": "bad", "poll_token": "p" * 32}).encode(),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            urllib.request.urlopen(request, context=context, timeout=3)
            raise AssertionError("unsigned route registration unexpectedly succeeded")
        except urllib.error.HTTPError as error:
            assert error.code == 403
    finally:
        service.stop()

