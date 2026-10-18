from __future__ import annotations

import copy
import base64
import json
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from backend.modules.aion_fabric.canonical import canonical_bytes
from backend.modules.aion_fabric.identity import IdentityStore
from backend.modules.aion_fabric.local_tls import LocalTLSAuthority
from backend.modules.aion_fabric.private_identity import ProductionPrivateIdentity
from backend.modules.pilot_unified.pairing import MobilePairingAuthority
from backend.modules.pilot_unified.pairing_service import MobilePairingService
from backend.modules.pilot_unified.opaque_relay import OpaqueRelayRouteAuthority, OpaqueRelayStore


CA_FINGERPRINT = "ab" * 32


def test_shared_tv_presence_accepts_only_local_client_addresses():
    assert MobilePairingService._is_trusted_local_address("192.168.18.113") is True
    assert MobilePairingService._is_trusted_local_address("127.0.0.1") is True
    assert MobilePairingService._is_trusted_local_address("fe80::1%en0") is True
    assert MobilePairingService._is_trusted_local_address("8.8.8.8") is False
    assert MobilePairingService._is_trusted_local_address("203.0.113.5") is False
    assert MobilePairingService._is_trusted_local_address("not-an-address") is False


def _authority(tmp_path):
    mother = IdentityStore(tmp_path / "mother_identity").load_or_create()
    identities = ProductionPrivateIdentity(tmp_path)
    profile = identities.onboard(display_name="Owner")
    authority = MobilePairingAuthority(
        tmp_path,
        mother_id="node_home_mother",
        mother_identity=mother,
        endpoint="https://pilot-home.local:8767",
        ca_sha256=CA_FINGERPRINT,
        identity_registry=identities,
    )
    return authority, mother, identities, profile


def _pair(authority, tmp_path, *, persona_id, scopes=("message.send", "task.create", "tv.control")):
    phone = IdentityStore(tmp_path / "phone_identity").load_or_create()
    challenge = authority.begin_pairing(
        persona_id=persona_id,
        device_label="Owner phone",
        phone_public_key=phone.public_key_b64,
        requested_scopes=scopes,
    )
    phone_challenge = challenge["phone_challenge"]
    signed = {
        key: phone_challenge[key]
        for key in (
            "schema_version", "challenge_id", "mother_id", "mother_fingerprint",
            "mother_descriptor_hash", "persona_id", "device_id", "device_label",
            "requested_scopes", "nonce", "issued_at", "expires_at",
        )
    }
    result = authority.complete_pairing(
        challenge_id=phone_challenge["challenge_id"],
        confirmation_code=challenge["local_confirmation"]["confirmation_code"],
        phone_signature=phone.sign(canonical_bytes(signed)),
    )
    return phone, challenge, result


def test_signed_descriptor_rejects_endpoint_and_key_substitution(tmp_path):
    authority, _, _, _ = _authority(tmp_path)
    descriptor = authority.mother_descriptor()
    assert authority.verify_mother_descriptor(descriptor, expected_fingerprint=descriptor["mother_fingerprint"])

    substituted = copy.deepcopy(descriptor)
    substituted["endpoint"] = "https://attacker.example"
    assert not authority.verify_mother_descriptor(substituted)
    assert not authority.verify_mother_descriptor(descriptor, expected_fingerprint="00" * 16)


def test_pairing_invitation_is_qr_safe_signed_and_tamper_evident(tmp_path):
    authority, _, _, profile = _authority(tmp_path)
    invitation = authority.pairing_invitation(
        persona_id=profile["persona_id"],
        requested_scopes=("task.create", "message.send"),
    )

    assert MobilePairingAuthority.verify_pairing_invitation(invitation) is True
    assert invitation["requested_scopes"] == ["message.send", "task.create"]
    assert invitation["contains_mother_secret"] is False
    assert invitation["contains_pairing_confirmation"] is False
    rendered = json.dumps(invitation)
    assert "confirmation_code" not in rendered
    assert "private_key" not in rendered

    altered_scope = copy.deepcopy(invitation)
    altered_scope["requested_scopes"].append("tv.control")
    assert MobilePairingAuthority.verify_pairing_invitation(altered_scope) is False

    altered_endpoint = copy.deepcopy(invitation)
    altered_endpoint["mother_descriptor"]["endpoint"] = "https://attacker.example"
    assert MobilePairingAuthority.verify_pairing_invitation(altered_endpoint) is False


def test_signed_descriptor_binds_the_public_tls_trust_anchor(tmp_path):
    mother = IdentityStore(tmp_path / "mother_identity").load_or_create()
    identities = ProductionPrivateIdentity(tmp_path)
    profile = identities.onboard(display_name="Owner")
    tls = LocalTLSAuthority(tmp_path).ensure(address="127.0.0.1", hostname="pilot-test.local")
    authority = MobilePairingAuthority(
        tmp_path,
        mother_id="node_home_mother",
        mother_identity=mother,
        endpoint="https://127.0.0.1:8770",
        ca_sha256=tls.ca_sha256,
        ca_certificate_pem=tls.ca_certificate_path.read_bytes(),
        identity_registry=identities,
    )
    invitation = authority.pairing_invitation(persona_id=profile["persona_id"])
    descriptor = invitation["mother_descriptor"]
    assert descriptor["schema_version"] == "pilot.mother-descriptor.v2"
    assert MobilePairingAuthority.verify_pairing_invitation(invitation) is True

    altered = copy.deepcopy(invitation)
    altered["mother_descriptor"]["ca_certificate_pem_b64"] = base64.b64encode(b"not a certificate").decode("ascii")
    assert MobilePairingAuthority.verify_pairing_invitation(altered) is False


def test_direct_remote_route_is_mother_signed_bounded_and_contains_no_secret(tmp_path):
    mother = IdentityStore(tmp_path / "mother_identity").load_or_create()
    identities = ProductionPrivateIdentity(tmp_path)
    profile = identities.onboard(display_name="Owner")
    authority = MobilePairingAuthority(
        tmp_path,
        mother_id="node_home_mother",
        mother_identity=mother,
        endpoint="https://pilot-home.local:8767",
        ca_sha256=CA_FINGERPRINT,
        identity_registry=identities,
        remote_endpoints=("https://pilot.example.test", "https://backup.example.test:9443"),
    )
    route = authority.direct_remote_route()
    assert route is not None
    assert route["endpoints"] == ["https://pilot.example.test", "https://backup.example.test:9443"]
    assert route["relay_used"] is False
    assert route["contains_mother_secret"] is False
    assert route["application_authentication"] == "signed_phone_possession"
    assert authority.verify_direct_remote_route(route, mother.public_key_b64) is True
    rendered = json.dumps(route)
    assert "private_key" not in rendered and "api_key" not in rendered

    changed = copy.deepcopy(route)
    changed["endpoints"] = ["https://attacker.example.test"]
    assert authority.verify_direct_remote_route(changed, mother.public_key_b64) is False

    _, _, paired = _pair(authority, tmp_path / "paired", persona_id=profile["persona_id"])
    assert authority.verify_direct_remote_route(paired["direct_remote_route"], mother.public_key_b64)


def test_direct_remote_route_rejects_unsafe_or_excessive_endpoints(tmp_path):
    mother = IdentityStore(tmp_path / "mother_identity").load_or_create()
    identities = ProductionPrivateIdentity(tmp_path)
    identities.onboard(display_name="Owner")
    with pytest.raises(ValueError, match="trusted HTTPS"):
        MobilePairingAuthority(
            tmp_path, mother_id="node_home_mother", mother_identity=mother,
            endpoint="https://pilot-home.local:8767", ca_sha256=CA_FINGERPRINT,
            identity_registry=identities, remote_endpoints=("http://unsafe.example.test",),
        )
    with pytest.raises(ValueError, match="at most four"):
        MobilePairingAuthority(
            tmp_path, mother_id="node_home_mother", mother_identity=mother,
            endpoint="https://pilot-home.local:8767", ca_sha256=CA_FINGERPRINT,
            identity_registry=identities,
            remote_endpoints=tuple(f"https://remote-{index}.example.test" for index in range(5)),
        )


def _relay_key(shared: bytes, request_id: str, direction: str) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None,
        info=canonical_bytes({"protocol": "pilot-opaque-relay-v1", "request_id": request_id, "direction": direction}),
    ).derive(shared)


def test_opaque_relay_is_signed_bounded_and_operator_unreadable(tmp_path):
    mother = IdentityStore(tmp_path / "mother_identity").load_or_create()
    identities = ProductionPrivateIdentity(tmp_path)
    profile = identities.onboard(display_name="Owner")
    authority = MobilePairingAuthority(
        tmp_path,
        mother_id="node_home_mother",
        mother_identity=mother,
        endpoint="https://pilot-home.local:8767",
        ca_sha256=CA_FINGERPRINT,
        identity_registry=identities,
        relay_endpoint="https://relay.customer.example",
    )
    route = authority.opaque_relay_route()
    assert route is not None
    assert OpaqueRelayRouteAuthority.verify_descriptor(route, mother.public_key_b64)
    assert route["operator_can_read_content"] is False
    assert route["contains_mother_secret"] is False
    assert route["content_encryption"] == "x25519_hkdf_sha256_aes_256_gcm"
    assert authority.opaque_relay.key_path.stat().st_mode & 0o777 == 0o600
    assert authority.opaque_relay.route_path.stat().st_mode & 0o777 == 0o600

    changed = copy.deepcopy(route)
    changed["mother_transport_public_key"] = base64.b64encode(b"x" * 32).decode("ascii")
    assert not OpaqueRelayRouteAuthority.verify_descriptor(changed, mother.public_key_b64)
    rendered = json.dumps(route)
    assert "private_key" not in rendered and "poll_token" not in rendered

    _, _, paired = _pair(authority, tmp_path / "paired_relay", persona_id=profile["persona_id"])
    assert OpaqueRelayRouteAuthority.verify_descriptor(paired["opaque_relay_route"], mother.public_key_b64)


def test_opaque_relay_round_trip_keeps_request_and_response_ciphertext_only(tmp_path):
    mother = IdentityStore(tmp_path / "mother_identity").load_or_create()
    identities = ProductionPrivateIdentity(tmp_path)
    identities.onboard(display_name="Owner")
    authority = OpaqueRelayRouteAuthority(
        tmp_path, mother_id="node_home_mother", mother_identity=mother,
        relay_endpoint="https://relay.customer.example",
    )
    descriptor = authority.descriptor()
    relay = OpaqueRelayStore()
    poll_token = "mother-poll-token-that-never-goes-to-the-phone"
    relay.register(descriptor, poll_token=poll_token)

    request_id = "relay_request_" + "1" * 32
    ephemeral = X25519PrivateKey.generate()
    mother_public = X25519PublicKey.from_public_bytes(base64.b64decode(descriptor["mother_transport_public_key"]))
    shared = ephemeral.exchange(mother_public)
    now = datetime.now(timezone.utc)
    metadata = {
        "schema_version": "pilot.opaque-relay-request.v1",
        "opaque_route_id": descriptor["opaque_route_id"],
        "request_id": request_id,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=60)).isoformat(),
        "ephemeral_public_key": base64.b64encode(ephemeral.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )).decode("ascii"),
    }
    secret_request = {"path": "/v1/personal/snapshot", "body": {"private": "Granada plans"}}
    nonce = b"r" * 12
    ciphertext = AESGCM(_relay_key(shared, request_id, "request")).encrypt(
        nonce, canonical_bytes(secret_request), canonical_bytes(metadata),
    )
    envelope = {
        **metadata, "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }
    accepted = relay.submit(envelope, submission_token=descriptor["submission_token"])
    assert accepted == {"accepted": True, "duplicate": False, "request_id": request_id}
    assert "Granada" not in json.dumps(envelope)
    assert relay.operator_view(descriptor["opaque_route_id"])["decryption_keys_held"] == 0
    assert relay.submit(envelope, submission_token=descriptor["submission_token"])["duplicate"] is True

    pulled = relay.pull(descriptor["opaque_route_id"], poll_token=poll_token)
    assert authority.open_request(pulled) == secret_request
    sealed = authority.seal_response(pulled, status=200, body={"private_result": "Available Friday"})
    relay.respond(sealed, poll_token=poll_token)
    delivered = relay.receive(
        descriptor["opaque_route_id"], request_id, submission_token=descriptor["submission_token"],
    )
    response_metadata = {key: delivered[key] for key in (
        "schema_version", "opaque_route_id", "request_id", "created_at", "expires_at",
    )}
    response_raw = AESGCM(_relay_key(shared, request_id, "response")).decrypt(
        base64.b64decode(delivered["nonce"]), base64.b64decode(delivered["ciphertext"]),
        canonical_bytes(response_metadata),
    )
    assert json.loads(response_raw) == {"body": {"private_result": "Available Friday"}, "status": 200}
    assert "Available Friday" not in json.dumps(delivered)


def test_opaque_relay_rejects_unsafe_endpoint_and_wrong_capabilities(tmp_path):
    mother = IdentityStore(tmp_path / "mother_identity").load_or_create()
    with pytest.raises(ValueError, match="trusted HTTPS"):
        OpaqueRelayRouteAuthority(
            tmp_path, mother_id="node_home_mother", mother_identity=mother,
            relay_endpoint="http://relay.example",
        )
    authority = OpaqueRelayRouteAuthority(
        tmp_path / "safe", mother_id="node_home_mother", mother_identity=mother,
        relay_endpoint="https://relay.example",
    )
    descriptor = authority.descriptor()
    relay = OpaqueRelayStore()
    relay.register(descriptor, poll_token="p" * 32)
    with pytest.raises(PermissionError):
        relay.pull(descriptor["opaque_route_id"], poll_token="wrong-token-that-is-long-enough")


def test_pairing_challenge_is_phone_bound_and_single_use(tmp_path):
    authority, _, identities, profile = _authority(tmp_path)
    phone, challenge, result = _pair(authority, tmp_path, persona_id=profile["persona_id"])
    assert result["connection"]["state"] == "connected"
    assert result["certificate"]["phone_public_key"] == phone.public_key_b64
    assert identities.device_status(persona_id=profile["persona_id"], device_id=result["certificate"]["device_id"])["status"] == "trusted"

    with pytest.raises(PermissionError, match="already been used"):
        authority.complete_pairing(
            challenge_id=challenge["phone_challenge"]["challenge_id"],
            confirmation_code=challenge["local_confirmation"]["confirmation_code"],
            phone_signature="invalid",
        )


def test_wrong_code_locks_bounded_challenge(tmp_path):
    authority, _, _, profile = _authority(tmp_path)
    phone = IdentityStore(tmp_path / "phone_identity").load_or_create()
    challenge = authority.begin_pairing(
        persona_id=profile["persona_id"],
        device_label="Owner phone",
        phone_public_key=phone.public_key_b64,
    )
    for attempt in range(authority.MAX_ATTEMPTS):
        with pytest.raises(PermissionError, match="does not match"):
            authority.complete_pairing(
                challenge_id=challenge["phone_challenge"]["challenge_id"],
                confirmation_code="999999",
                phone_signature="unused",
            )
    with pytest.raises(PermissionError, match="already been used"):
        authority.complete_pairing(
            challenge_id=challenge["phone_challenge"]["challenge_id"],
            confirmation_code=challenge["local_confirmation"]["confirmation_code"],
            phone_signature="unused",
        )


def test_certificate_lease_validation_and_lost_phone_revocation(tmp_path):
    authority, _, identities, profile = _authority(tmp_path)
    _, _, result = _pair(authority, tmp_path, persona_id=profile["persona_id"])
    certificate, lease = result["certificate"], result["lease"]
    assert authority.validate(certificate=certificate, lease=lease, required_scope="task.create")["valid"]
    with pytest.raises(PermissionError, match="not allowed"):
        authority.validate(certificate=certificate, lease=lease, required_scope="decision.approve")

    revoked = authority.revoke_device(device_id=certificate["device_id"], reason="lost phone")
    assert revoked["leases_revoked"] == 1
    assert revoked["shared_screen_authority_revoked"] is True
    assert authority.connection_state(device_id=certificate["device_id"])["state"] == "revoked"
    assert identities.device_status(persona_id=profile["persona_id"], device_id=certificate["device_id"])["status"] == "revoked"
    with pytest.raises(PermissionError, match="no longer trusted"):
        authority.validate(certificate=certificate, lease=lease, required_scope="task.create")


def test_lease_rotation_is_signed_replay_safe_and_cannot_expand_scope(tmp_path):
    authority, _, _, profile = _authority(tmp_path)
    phone, _, result = _pair(authority, tmp_path, persona_id=profile["persona_id"], scopes=("message.send", "task.create"))
    certificate, previous = result["certificate"], result["lease"]
    request = {
        "purpose": "renew_mobile_lease",
        "device_id": certificate["device_id"],
        "persona_id": certificate["persona_id"],
        "previous_lease_id": previous["lease_id"],
        "requested_scopes": ["message.send", "task.create"],
        "nonce": "renewal_nonce_123456",
    }
    renewed = authority.renew_lease(request, phone_signature=phone.sign(canonical_bytes(request)))
    assert renewed["previous_lease_id"] == previous["lease_id"]
    assert renewed["lease_id"] != previous["lease_id"]

    with pytest.raises(PermissionError, match="already been used"):
        authority.renew_lease(request, phone_signature=phone.sign(canonical_bytes(request)))

    expansion = {
        **request,
        "previous_lease_id": renewed["lease_id"],
        "requested_scopes": ["decision.approve", "message.send", "task.create"],
        "nonce": "renewal_nonce_654321",
    }
    with pytest.raises(PermissionError, match="silently add"):
        authority.renew_lease(expansion, phone_signature=phone.sign(canonical_bytes(expansion)))


def test_pairing_store_permissions_and_public_inventory(tmp_path):
    authority, _, _, profile = _authority(tmp_path)
    _, _, result = _pair(authority, tmp_path, persona_id=profile["persona_id"])
    assert authority.path.stat().st_mode & 0o777 == 0o600
    inventory = authority.inventory()
    assert inventory["count"] == 1
    assert "phone_public_key" not in inventory["devices"][0]
    assert inventory["devices"][0]["device_id"] == result["certificate"]["device_id"]


def test_identity_registry_revocation_immediately_blocks_mobile_authority(tmp_path):
    authority, _, identities, profile = _authority(tmp_path)
    phone, _, result = _pair(authority, tmp_path, persona_id=profile["persona_id"])
    certificate, lease = result["certificate"], result["lease"]
    identities.revoke_device(
        persona_id=profile["persona_id"],
        device_id=certificate["device_id"],
        reason="removed from identity settings",
    )
    with pytest.raises(PermissionError, match="no longer trusted"):
        authority.validate(certificate=certificate, lease=lease, required_scope="message.send")
    renewal = {
        "purpose": "renew_mobile_lease",
        "device_id": certificate["device_id"],
        "persona_id": certificate["persona_id"],
        "previous_lease_id": lease["lease_id"],
        "requested_scopes": list(lease["scopes"]),
        "nonce": "blocked_after_identity_revocation",
    }
    with pytest.raises(PermissionError, match="no longer trusted"):
        authority.renew_lease(renewal, phone_signature=phone.sign(canonical_bytes(renewal)))


def test_https_pairing_service_keeps_code_on_mother_and_enforces_origin(tmp_path):
    identities = ProductionPrivateIdentity(tmp_path)
    profile = identities.onboard(display_name="Owner")
    mother = IdentityStore(tmp_path / "mother_identity").load_or_create()
    tls = LocalTLSAuthority(tmp_path).ensure(address="127.0.0.1", hostname="pilot-test.local")
    authority = MobilePairingAuthority(
        tmp_path,
        mother_id="node_home_mother",
        mother_identity=mother,
        endpoint="https://127.0.0.1:8770",
        ca_sha256=tls.ca_sha256,
        identity_registry=identities,
    )
    presented = []
    class InboxProbe:
        def stream(self, *, persona_id, certificate, lease):
            assert persona_id == profile["persona_id"]
            assert certificate["device_id"] == lease["device_id"]
            return {"persona_id": persona_id, "revision": 7, "messages": [], "actions": [], "receipts": []}

    service = MobilePairingService(
        authority,
        tls_context=tls.context(),
        confirmation_presenter=presented.append,
        address="127.0.0.1",
        port=0,
        allowed_origins=("https://app.pilot.test",),
        inbox=InboxProbe(),
    )
    service.start()
    context = ssl.create_default_context(cafile=str(tls.ca_certificate_path))
    base = f"https://127.0.0.1:{service.port_in_use}"

    def request(path, *, payload=None, origin="https://app.pilot.test"):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Origin": origin}
        if body is not None:
            headers["Content-Type"] = "application/json"
        with urllib.request.urlopen(
            urllib.request.Request(base + path, data=body, headers=headers),
            context=context,
            timeout=3,
        ) as response:
            return response.status, json.loads(response.read())

    try:
        status, discovery = request("/.well-known/pilot-mother")
        assert status == 200
        assert authority.verify_mother_descriptor(discovery["descriptor"])
        assert discovery["trust_words"] == authority.trust_words()

        phone = IdentityStore(tmp_path / "phone_identity").load_or_create()
        status, challenge = request("/v1/pairing/challenges", payload={
            "persona_id": profile["persona_id"],
            "device_label": "Owner phone",
            "phone_public_key": phone.public_key_b64,
            "requested_scopes": ["message.send", "task.create"],
        })
        assert status == 201
        assert len(presented) == 1
        assert "confirmation_code" not in challenge
        assert presented[0]["challenge_id"] == challenge["challenge_id"]

        signed = {
            key: challenge[key]
            for key in (
                "schema_version", "challenge_id", "mother_id", "mother_fingerprint",
                "mother_descriptor_hash", "persona_id", "device_id", "device_label",
                "requested_scopes", "nonce", "issued_at", "expires_at",
            )
        }
        status, paired = request("/v1/pairing/complete", payload={
            "challenge_id": challenge["challenge_id"],
            "confirmation_code": presented[0]["confirmation_code"],
            "phone_signature": phone.sign(canonical_bytes(signed)),
        })
        assert status == 200
        assert paired["connection"]["state"] == "connected"
        assert authority.validate(
            certificate=paired["certificate"],
            lease=paired["lease"],
            required_scope="task.create",
        )["valid"]

        status, stream = request("/v1/inbox/stream", payload={
            "persona_id": profile["persona_id"],
            "certificate": paired["certificate"],
            "lease": paired["lease"],
        })
        assert status == 200
        assert stream == {"persona_id": profile["persona_id"], "revision": 7, "messages": [], "actions": [], "receipts": []}

        with pytest.raises(urllib.error.HTTPError) as denied:
            request("/.well-known/pilot-mother", origin="https://impostor.example")
        assert denied.value.code == 403
    finally:
        service.stop()
