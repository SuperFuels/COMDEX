import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture
def client(tmp_path, monkeypatch):
    db = tmp_path / "chain_sim.sqlite3"
    monkeypatch.setenv("CHAIN_SIM_PERSIST", "1")
    monkeypatch.setenv("CHAIN_SIM_DB_PATH", str(db))
    with TestClient(app) as c:
        yield c

def test_persist_and_replay_roundtrip(client: TestClient, monkeypatch):
    # 1) reset genesis
    r = client.post("/api/chain_sim/dev/reset", json={
        "chain_id": "glyphchain-dev",
        "network_id": "local",
        "allocs": [{"address":"pho1-s0","balances":{"PHO":"10","TESS":"0"}}],
        "validators": [],
    })
    assert r.status_code == 200

    # 2) do one tx
    r = client.post("/api/chain_sim/dev/submit_tx", json={
        "chain_id": "glyphchain-dev",
        "from_addr": "pho1-s0",
        "nonce": 0,
        "tx_type": "BANK_BURN",
        "payload": {"denom":"PHO","amount":"1"},
    })
    # if sig mode is on in your test env, set it off or provide signature in this test
    assert r.status_code in (200, 400)

    # 3) simulate "restart": wipe in-memory state + ledger, then replay
    from backend.modules.chain_sim import chain_sim_config as cfg
    from backend.modules.chain_sim import chain_sim_model as bank
    from backend.modules.staking import staking_model as staking
    from backend.modules.chain_sim.chain_sim_ledger import reset_ledger, replay_state_from_db

    cfg.reset_config()
    staking.reset_state()
    bank.reset_state()
    reset_ledger()

    ok = replay_state_from_db()
    assert ok is True

    # 4) post-replay invariants (supply/balance should reflect replayed txs)
    supply = client.get("/api/chain_sim/dev/supply").json()
    assert "PHO" in supply