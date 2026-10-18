from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from backend.modules.p2p.crypto_ed25519 import pubkey_from_priv
from backend.modules.p2p.peer_discovery import (
    PeerDiscoveryError,
    SCHEMA_VERSION,
    SignedPeerDiscoveryStore,
    sign_discovery_record,
)


NOW = 1_800_000_000


def _keys():
    private = Ed25519PrivateKey.generate().private_bytes_raw().hex()
    return private, pubkey_from_priv(private)


def _record(private, *, sequence=1, node="node-a", expires=NOW + 3600):
    return sign_discovery_record({
        "schema_version": SCHEMA_VERSION,
        "chain_id": "glyphchain-main",
        "authority_id": "release-bootstrap",
        "sequence": sequence,
        "issued_at": NOW - 10,
        "expires_at": expires,
        "peers": [{
            "node_id": node,
            "base_url": "https://relay.example.com",
            "role": "relay",
            "val_id": None,
            "pubkey_hex": "11" * 32,
        }],
    }, private)


def test_signed_discovery_requires_pinned_authority_and_persists_latest_record(tmp_path):
    private, public = _keys()
    service = SignedPeerDiscoveryStore(
        tmp_path, chain_id="glyphchain-main", trust_anchors={"release-bootstrap": public}, clock=lambda: NOW,
    )
    result = service.import_record(_record(private))
    assert result["accepted"] is True
    assert service.active_peers()[0]["node_id"] == "node-a"
    restarted = SignedPeerDiscoveryStore(
        tmp_path, chain_id="glyphchain-main", trust_anchors={"release-bootstrap": public}, clock=lambda: NOW,
    )
    assert restarted.status()["active_peer_count"] == 1
    assert restarted.import_record(_record(private))["duplicate"] is True


def test_signature_chain_expiry_and_untrusted_authority_are_rejected(tmp_path):
    private, public = _keys()
    service = SignedPeerDiscoveryStore(
        tmp_path, chain_id="glyphchain-main", trust_anchors={"release-bootstrap": public}, clock=lambda: NOW,
    )
    tampered = _record(private)
    tampered["peers"][0]["base_url"] = "https://attacker.example.com"
    with pytest.raises(PeerDiscoveryError, match="discovery_signature_invalid"):
        service.import_record(tampered)
    expired = _record(private, expires=NOW)
    with pytest.raises(PeerDiscoveryError, match="discovery_record_expired"):
        service.import_record(expired)
    wrong = dict(_record(private)); wrong["authority_id"] = "unknown"
    with pytest.raises(PeerDiscoveryError, match="discovery_authority_not_trusted"):
        service.import_record(wrong)


def test_sequence_replay_and_equivocation_are_rejected(tmp_path):
    private, public = _keys()
    service = SignedPeerDiscoveryStore(
        tmp_path, chain_id="glyphchain-main", trust_anchors={"release-bootstrap": public}, clock=lambda: NOW,
    )
    service.import_record(_record(private, sequence=2, node="node-b"))
    with pytest.raises(PeerDiscoveryError, match="discovery_record_replay"):
        service.import_record(_record(private, sequence=1))
    with pytest.raises(PeerDiscoveryError, match="discovery_sequence_equivocation"):
        service.import_record(_record(private, sequence=2, node="node-c"))


def test_production_records_require_https_public_addresses_and_bound_size(tmp_path):
    private, public = _keys()
    service = SignedPeerDiscoveryStore(
        tmp_path, chain_id="glyphchain-main", trust_anchors={"release-bootstrap": public}, clock=lambda: NOW,
    )
    local = _record(private); local["peers"][0]["base_url"] = "http://127.0.0.1:8080"
    local = sign_discovery_record({key: value for key, value in local.items() if key != "signature_hex"}, private)
    with pytest.raises(PeerDiscoveryError, match="discovery_peer_transport_invalid"):
        service.import_record(local)
    too_many = {key: value for key, value in _record(private).items() if key != "signature_hex"}
    too_many["peers"] = too_many["peers"] * 101
    too_many = sign_discovery_record(too_many, private)
    with pytest.raises(PeerDiscoveryError, match="discovery_peer_count_invalid"):
        service.import_record(too_many)


def test_development_mode_can_explicitly_allow_private_bootstrap_addresses(tmp_path):
    private, public = _keys()
    service = SignedPeerDiscoveryStore(
        tmp_path, chain_id="glyphchain-main", trust_anchors={"release-bootstrap": public},
        clock=lambda: NOW, allow_private_addresses=True,
    )
    local = {key: value for key, value in _record(private).items() if key != "signature_hex"}
    local["peers"][0]["base_url"] = "http://127.0.0.1:8080"
    assert service.import_record(sign_discovery_record(local, private))["accepted"] is True
