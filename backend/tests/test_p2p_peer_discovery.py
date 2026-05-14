import os
from fastapi.testclient import TestClient
from backend.main import app

def test_p2p_hello_rejects_wrong_chain_id(monkeypatch):
    monkeypatch.setenv("GLYPHCHAIN_CHAIN_ID", "glyphchain-dev")
    c = TestClient(app)

    r = c.post("/api/p2p/hello", json={
        "type": "HELLO",
        "from_node_id": "nX",
        "chain_id": "wrong-chain",
        "base_url": "http://127.0.0.1:9999",
        "payload": {},
        "hops": 0,
        "ts_ms": 0
    })
    assert r.status_code == 400
    assert "chain_id mismatch" in r.text

def test_p2p_hello_adds_peer(monkeypatch):
    monkeypatch.setenv("GLYPHCHAIN_CHAIN_ID", "glyphchain-dev")
    c = TestClient(app)

    r = c.post("/api/p2p/hello", json={
        "type": "HELLO",
        "from_node_id": "n2",
        "from_val_id": "pho1-dev-val2",
        "chain_id": "glyphchain-dev",
        "base_url": "http://127.0.0.1:18081",
        "role": "validator",
        "payload": {},
        "hops": 0,
        "ts_ms": 0
    })
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] is True
    assert j["peer"]["node_id"] == "n2"