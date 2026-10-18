from backend.modules.p2p.peer_store import (
    _reset_peer_store_for_tests,
    add_peer,
    find_peer_by_val_id,
    list_peers,
    peer_store_status,
    set_peer_identity,
)


def test_peer_store_is_bounded_and_removes_evicted_validator_alias(monkeypatch):
    _reset_peer_store_for_tests()
    monkeypatch.setenv("GLYPHCHAIN_MAX_PEERS", "8")
    for index in range(8):
        peer = add_peer(f"https://peer-{index}.example.com", f"node-{index}", f"val-{index}", "peer")
        peer.last_seen_ms = float(index)
    add_peer("https://new.example.com", "node-new", "val-new", "peer")
    assert len(list_peers()) == 8
    assert find_peer_by_val_id("val-0") is None
    assert find_peer_by_val_id("val-new").node_id == "node-new"
    assert peer_store_status() == {"peer_count": 8, "peer_limit": 8}
    _reset_peer_store_for_tests()


def test_peer_store_prefers_retaining_validator_and_identity_updates_do_not_bypass_limit(monkeypatch):
    _reset_peer_store_for_tests()
    monkeypatch.setenv("GLYPHCHAIN_MAX_PEERS", "8")
    validator = add_peer("https://validator.example.com", "validator", "validator-1", "validator")
    validator.last_seen_ms = 0
    for index in range(7):
        peer = add_peer(f"https://peer-{index}.example.com", f"node-{index}", None, "peer")
        peer.last_seen_ms = float(index + 1)
    set_peer_identity(
        node_id="identity-new", base_url="https://identity.example.com", val_id=None,
        pubkey_hex="22" * 32, hello_ok=True,
    )
    assert len(list_peers()) == 8
    assert any(peer.node_id == "validator" for peer in list_peers())
    assert any(peer.node_id == "identity-new" for peer in list_peers())
    _reset_peer_store_for_tests()


def test_peer_store_rejects_unbounded_identity_fields(monkeypatch):
    _reset_peer_store_for_tests()
    monkeypatch.setenv("GLYPHCHAIN_MAX_PEERS", "8")
    try:
        add_peer("https://peer.example.com", "n" * 181)
    except ValueError as exc:
        assert str(exc) == "peer_node_id_too_long"
    else:
        raise AssertionError("oversized peer identity was accepted")
    _reset_peer_store_for_tests()
