from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from backend.modules.p2p.crypto_ed25519 import pubkey_from_priv
from backend.modules.p2p.crypto_ed25519 import canonical_hello_sign_bytes, sign_ed25519, verify_ed25519
from backend.modules.p2p.nat_relay import (
    NATRelayError,
    NATRelayLimits,
    NATRelayStore,
    SCHEMA_VERSION,
    build_relay_operation,
    verify_relay_operation,
)
from backend.modules.p2p.peer_discovery import SignedPeerDiscoveryStore, sign_discovery_record
from backend.modules.p2p.p2p_types import PeerInfo
from backend.modules.p2p.p2p_types import P2PEnvelope
from fastapi import HTTPException
from starlette.requests import Request


pytestmark = pytest.mark.glyphchain


def _private() -> str:
    return Ed25519PrivateKey.generate().private_bytes_raw().hex()


def _envelope(sender: str = "node-a", message_type: str = "PROPOSAL") -> dict:
    return {
        "type": message_type,
        "from_node_id": sender,
        "from_val_id": "val-a",
        "chain_id": "glyphchain-main",
        "ts_ms": 1_800_000_000_000,
        "payload": {"height": 8, "round": 0, "block_id": "block-8"},
        "hops": 0,
    }


def test_relay_operation_is_chain_time_and_signature_bound():
    private = _private()
    operation = build_relay_operation(
        operation="PULL", chain_id="glyphchain-main", node_id="node-a",
        private_key_hex=private, payload={"limit": 10}, clock_ms=lambda: 1_000_000,
    )
    verified = verify_relay_operation(
        operation, expected_chain_id="glyphchain-main",
        public_key_hex=pubkey_from_priv(private), clock_ms=lambda: 1_000_010,
    )
    assert verified["operation"] == "PULL"
    changed = dict(operation); changed["limit"] = 11
    with pytest.raises(NATRelayError, match="nat_relay_signature_invalid"):
        verify_relay_operation(
            changed, expected_chain_id="glyphchain-main",
            public_key_hex=pubkey_from_priv(private), clock_ms=lambda: 1_000_010,
        )
    with pytest.raises(NATRelayError, match="nat_relay_chain_mismatch"):
        verify_relay_operation(
            operation, expected_chain_id="other",
            public_key_hex=pubkey_from_priv(private), clock_ms=lambda: 1_000_010,
        )
    with pytest.raises(NATRelayError, match="nat_relay_timestamp_outside_window"):
        verify_relay_operation(
            operation, expected_chain_id="glyphchain-main",
            public_key_hex=pubkey_from_priv(private), clock_ms=lambda: 2_000_000,
        )


def test_relay_queue_is_durable_idempotent_and_recipient_acknowledged(tmp_path):
    now = [1_000_000]
    limits = NATRelayLimits(maximum_messages=8, maximum_per_target=4, maximum_message_bytes=4096,
                            maximum_ttl_ms=60_000, pull_batch=3)
    store = NATRelayStore(tmp_path, chain_id="glyphchain-main", limits=limits, clock_ms=lambda: now[0])
    first = store.put(
        from_node_id="node-a", target_node_id="node-b", envelope=_envelope(), ttl_ms=30_000,
    )
    duplicate = store.put(
        from_node_id="node-a", target_node_id="node-b", envelope=_envelope(), ttl_ms=30_000,
    )
    assert first["accepted"] is True and first["duplicate"] is False
    assert duplicate == {"accepted": True, "duplicate": True, "relay_id": first["relay_id"]}
    restarted = NATRelayStore(tmp_path, chain_id="glyphchain-main", limits=limits, clock_ms=lambda: now[0])
    pulled = restarted.pull(target_node_id="node-b")
    assert [item["relay_id"] for item in pulled["messages"]] == [first["relay_id"]]
    assert pulled["messages"][0]["delivery_attempts"] == 1
    assert restarted.pull(target_node_id="node-c")["messages"] == []
    assert restarted.ack(target_node_id="node-c", relay_ids=[first["relay_id"]])["acknowledged"] == 0
    assert restarted.ack(target_node_id="node-b", relay_ids=[first["relay_id"]])["acknowledged"] == 1
    assert restarted.status()["queued_messages"] == 0


def test_relay_queue_expires_and_fails_closed_at_bounds(tmp_path):
    now = [1_000_000]
    limits = NATRelayLimits(maximum_messages=2, maximum_per_target=1, maximum_message_bytes=1024,
                            maximum_ttl_ms=10_000, pull_batch=2)
    store = NATRelayStore(tmp_path, chain_id="glyphchain-main", limits=limits, clock_ms=lambda: now[0])
    store.put(from_node_id="node-a", target_node_id="node-b", envelope=_envelope(), ttl_ms=2_000)
    with pytest.raises(NATRelayError, match="nat_relay_target_queue_full"):
        store.put(from_node_id="node-c", target_node_id="node-b", envelope=_envelope("node-c"), ttl_ms=2_000)
    with pytest.raises(NATRelayError, match="nat_relay_sender_mismatch"):
        store.put(from_node_id="node-c", target_node_id="node-d", envelope=_envelope("node-a"), ttl_ms=2_000)
    now[0] += 2_001
    assert store.pull(target_node_id="node-b")["messages"] == []
    assert store.status()["queued_messages"] == 0


def test_relay_queue_rejects_request_response_lanes_without_correlation(tmp_path):
    store = NATRelayStore(tmp_path, chain_id="glyphchain-main")
    for message_type in ("STATUS", "SYNC_REQ", "SYNC_RESP", "BLOCK_REQ", "SNAPSHOT_REQ"):
        with pytest.raises(NATRelayError, match="nat_relay_message_type_invalid"):
            store.put(
                from_node_id="node-a", target_node_id="node-b",
                envelope=_envelope("node-a", message_type), ttl_ms=30_000,
            )


def test_signed_discovery_binds_nat_relay_route(tmp_path):
    authority = _private()
    peer_private = _private()
    now = 1_800_000_000
    service = SignedPeerDiscoveryStore(
        tmp_path, chain_id="glyphchain-main",
        trust_anchors={"release": pubkey_from_priv(authority)}, clock=lambda: now,
    )
    record = sign_discovery_record({
        "schema_version": "glyphchain.peer-discovery.v1",
        "chain_id": "glyphchain-main", "authority_id": "release", "sequence": 1,
        "issued_at": now - 1, "expires_at": now + 3600,
        "peers": [{
            "node_id": "home-node", "base_url": "https://unreachable.example.com",
            "relay_url": "https://relay.example.com", "role": "light", "val_id": None,
            "pubkey_hex": pubkey_from_priv(peer_private),
        }],
    }, authority)
    assert service.import_record(record)["accepted"] is True
    assert service.active_peers()[0]["relay_url"] == "https://relay.example.com"
    tampered = dict(record); tampered["peers"] = [dict(record["peers"][0])]
    tampered["peers"][0]["relay_url"] = "https://attacker.example.com"
    with pytest.raises(Exception, match="discovery_signature_invalid"):
        service.import_record(tampered)


@pytest.mark.asyncio
async def test_consensus_broadcast_uses_relay_route_without_direct_post(monkeypatch):
    from backend.modules.consensus import net

    peer = PeerInfo(
        node_id="home-node", base_url="https://unreachable.example.com",
        relay_url="https://relay.example.com", role="light",
    )
    captured = {}

    async def fake_enqueue(**kwargs):
        captured.update(kwargs)
        return {"ok": True, "accepted": True}

    async def no_direct(*args, **kwargs):
        raise AssertionError("direct transport must not be attempted for a relay-routed peer")

    monkeypatch.setattr(net, "enqueue_via_nat_relay", fake_enqueue)
    monkeypatch.setattr(net, "post_json", no_direct)
    result = await net._post_peer_or_nat_relay(
        peer, path="/api/p2p/proposal", envelope=_envelope(),
        chain_id="glyphchain-main", from_node_id="node-a", from_val_id="val-a", timeout_s=3.0,
    )
    assert result["accepted"] is True
    assert captured["relay_url"] == "https://relay.example.com"
    assert captured["target_node_id"] == "home-node"


@pytest.mark.asyncio
async def test_relay_api_requires_verified_hello_role_signature_and_fresh_nonce(tmp_path, monkeypatch):
    from backend.modules.p2p import router
    from backend.modules.p2p.peer_store import _reset_peer_store_for_tests, add_peer, set_peer_identity

    private = _private()
    _reset_peer_store_for_tests()
    add_peer("https://home.example.com", "node-a", role="light")
    add_peer("https://target.example.com", "node-b", role="light")
    set_peer_identity(
        node_id="node-a", base_url="https://home.example.com", val_id=None,
        pubkey_hex=pubkey_from_priv(private), hello_ok=True,
    )
    set_peer_identity(
        node_id="node-b", base_url="https://target.example.com", val_id=None,
        pubkey_hex=pubkey_from_priv(_private()), hello_ok=False,
    )
    monkeypatch.setattr(router, "_CHAIN_ID", "glyphchain-main")
    monkeypatch.setattr(
        router, "participation_from_env",
        lambda: {"role": "relay", "capabilities": {"relay_messages": True}},
    )
    monkeypatch.setattr(
        router, "_NAT_RELAY_STORE",
        NATRelayStore(tmp_path, chain_id="glyphchain-main", clock_ms=lambda: 1_000_000),
    )
    monkeypatch.setattr(router.time, "time", lambda: 1_000.0)
    router._NAT_NONCES.clear()
    put = build_relay_operation(
        operation="PUT", chain_id="glyphchain-main", node_id="node-a",
        private_key_hex=private,
        payload={"target_node_id": "node-b", "ttl_ms": 30_000, "envelope": _envelope()},
        clock_ms=lambda: 1_000_000,
    )
    assert (await router.p2p_nat_put(put))["accepted"] is True
    with pytest.raises(HTTPException) as replay:
        await router.p2p_nat_put(put)
    assert replay.value.status_code == 409

    # Restarting the relay store does not reopen the signed-operation replay
    # window.  The raw nonce is not retained in the durable journal.
    monkeypatch.setattr(
        router, "_NAT_RELAY_STORE",
        NATRelayStore(tmp_path, chain_id="glyphchain-main", clock_ms=lambda: 1_000_000),
    )
    router._NAT_NONCES.clear()
    with pytest.raises(HTTPException) as restart_replay:
        await router.p2p_nat_put(put)
    assert restart_replay.value.status_code == 409
    replay_bytes = (tmp_path / "nat-relay-replay.json").read_bytes()
    assert str(put["nonce"]).encode("utf-8") not in replay_bytes
    pull = build_relay_operation(
        operation="PULL", chain_id="glyphchain-main", node_id="node-a",
        private_key_hex=private, payload={"limit": 10}, clock_ms=lambda: 1_000_000,
    )
    assert (await router.p2p_nat_pull(pull))["messages"] == []
    monkeypatch.setattr(
        router, "participation_from_env",
        lambda: {"role": "light", "capabilities": {"relay_messages": False}},
    )
    fresh = build_relay_operation(
        operation="PULL", chain_id="glyphchain-main", node_id="node-a",
        private_key_hex=private, payload={"limit": 10}, clock_ms=lambda: 1_000_000,
    )
    with pytest.raises(HTTPException) as denied:
        await router.p2p_nat_pull(fresh)
    assert denied.value.status_code == 403


@pytest.mark.asyncio
async def test_outbound_client_dispatches_original_envelope_locally_before_ack(monkeypatch):
    from backend.modules.p2p import router

    private = _private()
    envelope = _envelope("node-a", "PROPOSAL")
    operations = []

    async def fake_relay_post(**kwargs):
        operation = dict(kwargs["operation"])
        operations.append(operation)
        if operation["operation"] == "PULL":
            return {
                "status": 200,
                "json": {"ok": True, "messages": [{"relay_id": "nat-1", "envelope": envelope}]},
                "text": "",
            }
        return {"status": 200, "json": {"ok": True, "acknowledged": 1}, "text": ""}

    locally_delivered = []

    async def fake_local_post(base, path, body, **kwargs):
        locally_delivered.append((base, path, body, kwargs))
        return {"status": 200, "status_code": 200, "json": {"ok": True}, "text": ""}

    monkeypatch.setattr(router, "_CHAIN_ID", "glyphchain-main")
    monkeypatch.setattr(router, "_NODE_ID", "node-b")
    monkeypatch.setattr(router, "relay_post", fake_relay_post)
    monkeypatch.setattr(router, "post_json", fake_local_post)
    monkeypatch.setattr(router, "active_transport_private_key", lambda **kwargs: private)
    result = await router._nat_relay_pull_once("https://relay.example.com")
    assert result == {"received": 1, "delivered": 1, "rejected": 0}
    assert locally_delivered[0][1] == "/api/p2p/proposal"
    assert locally_delivered[0][2] == envelope
    assert locally_delivered[0][3]["p2p_from_node_id"] == "node-a"
    assert [operation["operation"] for operation in operations] == ["PULL", "ACK"]
    assert operations[1]["relay_ids"] == ["nat-1"]


@pytest.mark.asyncio
async def test_one_way_hello_returns_signed_responder_and_enforces_discovery_binding(monkeypatch):
    from backend.modules.p2p import router
    from backend.modules.p2p.peer_store import _reset_peer_store_for_tests, add_peer, set_peer_identity

    local_private = _private()
    remote_private = _private()
    remote_public = pubkey_from_priv(remote_private)
    _reset_peer_store_for_tests()
    add_peer("https://remote.example.com", "remote", role="light")
    set_peer_identity(
        node_id="remote", base_url="https://remote.example.com", val_id=None,
        pubkey_hex=remote_public, hello_ok=False,
    )
    monkeypatch.setattr(router, "_CHAIN_ID", "glyphchain-main")
    monkeypatch.setattr(router, "_NODE_ID", "relay")
    monkeypatch.setattr(router, "_BASE_URL", "https://relay.example.com")
    monkeypatch.setattr(router, "_SELF_VAL_ID", "")
    monkeypatch.setattr(router, "_active_transport_private_key_hex", lambda: local_private)
    monkeypatch.setattr(router, "active_transport_private_key", lambda **kwargs: local_private)
    monkeypatch.setenv("GLYPHCHAIN_BASE_URL", "https://relay.example.com")
    monkeypatch.setenv("GLYPHCHAIN_REQUIRE_SIGNED_DISCOVERY", "1")
    hello_bytes = canonical_hello_sign_bytes(
        chain_id="glyphchain-main", node_id="remote", val_id=None,
        base_url="https://remote.example.com", pubkey_hex=remote_public,
    )
    envelope = P2PEnvelope(
        type="HELLO", from_node_id="remote", chain_id="glyphchain-main", ts_ms=1,
        base_url="https://remote.example.com",
        payload={
            "base_url": "https://remote.example.com", "pubkey_hex": remote_public,
            "sig_hex": sign_ed25519(remote_private, hello_bytes), "is_reply": True,
        },
    )
    request = Request({"type": "http", "method": "POST", "path": "/api/p2p/hello", "headers": []})
    response = await router.p2p_hello(request, envelope)
    responder = response["responder"]
    responder_payload = responder["payload"]
    responder_bytes = canonical_hello_sign_bytes(
        chain_id="glyphchain-main", node_id="relay", val_id=None,
        base_url="https://relay.example.com", pubkey_hex=responder_payload["pubkey_hex"],
        protocol=responder_payload["protocol"],
    )
    assert verify_ed25519(
        responder_payload["pubkey_hex"], responder_payload["sig_hex"], responder_bytes,
    )
    unknown_private = _private()
    unknown_public = pubkey_from_priv(unknown_private)
    unknown_bytes = canonical_hello_sign_bytes(
        chain_id="glyphchain-main", node_id="unknown", val_id=None,
        base_url="https://unknown.example.com", pubkey_hex=unknown_public,
    )
    unknown = P2PEnvelope(
        type="HELLO", from_node_id="unknown", chain_id="glyphchain-main", ts_ms=1,
        base_url="https://unknown.example.com",
        payload={
            "base_url": "https://unknown.example.com", "pubkey_hex": unknown_public,
            "sig_hex": sign_ed25519(unknown_private, unknown_bytes), "is_reply": True,
        },
    )
    with pytest.raises(HTTPException) as rejected:
        await router.p2p_hello(request, unknown)
    assert rejected.value.status_code == 403
