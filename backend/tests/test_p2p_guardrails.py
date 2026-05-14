# backend/tests/test_p2p_guardrails.py
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from backend.main import app


def _reset_dev_chain(c: TestClient) -> None:
    genesis = {
        "chain_id": "glyphchain-dev",
        "network_id": "devnet",
        "allocs": [
            {"address": "pho1-dev-val1", "balances": {"PHO": "1000", "TESS": "1000"}},
            {"address": "pho1-dev-val2", "balances": {"PHO": "1000", "TESS": "1000"}},
            {"address": "pho1-dev-user1", "balances": {"PHO": "1000", "TESS": "0"}},
        ],
        "validators": [
            {"address": "pho1-dev-val1", "power": "100", "commission": "0"},
            {"address": "pho1-dev-val2", "power": "100", "commission": "0"},
        ],
    }
    r = c.post("/api/chain_sim/dev/reset", json=genesis)
    assert r.status_code == 200, r.text


def test_submit_tx_async_rejects_wrong_p2p_chain_id(monkeypatch: pytest.MonkeyPatch) -> None:
    # ensure async ingest is enabled + signatures won't block this test
    monkeypatch.setenv("CHAIN_SIM_ASYNC_ENABLED", "1")
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "off")
    monkeypatch.setenv("GLYPHCHAIN_CHAIN_ID", "glyphchain-dev")
    monkeypatch.setenv("GLYPHCHAIN_SELF_VAL_ID", "pho1-dev-val1")

    c = TestClient(app)
    _reset_dev_chain(c)

    tx = {
        "from_addr": "pho1-dev-user1",
        "nonce": 1,
        "tx_type": "BANK_SEND",
        "payload": {"to": "pho1-dev-val1", "denom": "PHO", "amount": "1"},
    }

    r = c.post(
        "/api/chain_sim/dev/submit_tx_async",
        json=tx,
        headers={
            "x-glyphchain-p2p-node-id": "peer-node-1",
            "x-glyphchain-p2p-chain-id": "wrong-chain",
        },
    )
    assert r.status_code == 400, r.text
    j = r.json()
    assert "wrong chain_id" in (j.get("detail") or "")


def test_submit_tx_async_rate_limits_only_when_peer_headers_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHAIN_SIM_ASYNC_ENABLED", "1")
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "off")
    monkeypatch.setenv("GLYPHCHAIN_CHAIN_ID", "glyphchain-dev")
    monkeypatch.setenv("GLYPHCHAIN_SELF_VAL_ID", "pho1-dev-val1")

    # make rate limit deterministic: allow 1 msg burst, refill rate 0 => 2nd msg gets 429
    monkeypatch.setenv("P2P_RL_MSG_PER_SEC", "0")
    monkeypatch.setenv("P2P_RL_MSG_BURST", "1")
    monkeypatch.setenv("P2P_RL_BYTES_PER_SEC", "99999999")
    monkeypatch.setenv("P2P_RL_BYTES_BURST", "99999999")

    # clear buckets so the test is stable even when run repeatedly in same process
    from backend.modules.p2p import rate_limit as rl

    rl._BUCKETS.clear()

    c = TestClient(app)
    _reset_dev_chain(c)

    tx = {
        "from_addr": "pho1-dev-user1",
        "nonce": 1,
        "tx_type": "BANK_SEND",
        "payload": {"to": "pho1-dev-val1", "denom": "PHO", "amount": "1"},
    }

    headers = {
        "x-glyphchain-p2p-node-id": "peer-node-rate-test",
        "x-glyphchain-p2p-chain-id": "glyphchain-dev",
    }

    r1 = c.post("/api/chain_sim/dev/submit_tx_async", json=tx, headers=headers)
    assert r1.status_code == 202, r1.text

    r2 = c.post("/api/chain_sim/dev/submit_tx_async", json=tx, headers=headers)
    assert r2.status_code == 429, r2.text

    # and: without peer headers, do NOT rate limit (should be handled normally)
    rl._BUCKETS.clear()
    r3 = c.post("/api/chain_sim/dev/submit_tx_async", json=tx)
    assert r3.status_code == 202, r3.text

def test_rate_limit_peer_key_prefers_val_id_over_node_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHAIN_SIM_ASYNC_ENABLED", "1")
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "off")
    monkeypatch.setenv("GLYPHCHAIN_CHAIN_ID", "glyphchain-dev")
    monkeypatch.setenv("GLYPHCHAIN_SELF_VAL_ID", "pho1-dev-val1")

    # allow 1 msg burst, refill 0 => 2nd msg (same peer_key) gets 429
    monkeypatch.setenv("P2P_RL_MSG_PER_SEC", "0")
    monkeypatch.setenv("P2P_RL_MSG_BURST", "1")
    monkeypatch.setenv("P2P_RL_BYTES_PER_SEC", "99999999")
    monkeypatch.setenv("P2P_RL_BYTES_BURST", "99999999")

    from backend.modules.p2p import rate_limit as rl

    rl._BUCKETS.clear()

    c = TestClient(app)
    _reset_dev_chain(c)

    tx = {
        "from_addr": "pho1-dev-user1",
        "nonce": 1,
        "tx_type": "BANK_SEND",
        "payload": {"to": "pho1-dev-val1", "denom": "PHO", "amount": "1"},
    }

    # same val-id, different node-id => should still be same peer_key => 2nd call hits 429
    h1 = {
        "x-glyphchain-p2p-node-id": "node-A",
        "x-glyphchain-p2p-val-id": "pho1-dev-val2",
        "x-glyphchain-p2p-chain-id": "glyphchain-dev",
    }
    h2 = {
        "x-glyphchain-p2p-node-id": "node-B",
        "x-glyphchain-p2p-val-id": "pho1-dev-val2",
        "x-glyphchain-p2p-chain-id": "glyphchain-dev",
    }

    r1 = c.post("/api/chain_sim/dev/submit_tx_async", json=tx, headers=h1)
    assert r1.status_code == 202, r1.text

    r2 = c.post("/api/chain_sim/dev/submit_tx_async", json=tx, headers=h2)
    assert r2.status_code == 429, r2.text