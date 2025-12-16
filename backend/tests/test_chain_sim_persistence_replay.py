# backend/tests/test_chain_sim_persistence_replay.py

import importlib
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    db = tmp_path / "chain_sim.sqlite3"

    monkeypatch.setenv("CHAIN_SIM_PERSIST", "1")
    monkeypatch.setenv("CHAIN_SIM_DB_PATH", str(db))
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "off")
    monkeypatch.setenv("CHAIN_SIM_PERSIST_DEBUG", "1")
    monkeypatch.setenv("CHAIN_SIM_ASYNC_ENABLED", "0")  # deterministic

    import backend.main as main
    importlib.reload(main)  # ensure env is seen during imports
    app = main.app

    with TestClient(app) as c:
        yield c


def _clear_ledger_only(l):
    # clear in-memory ledger only (DO NOT wipe sqlite)
    l._BLOCKS.clear()
    l._TXS.clear()
    l._TX_BY_ID.clear()
    l._TX_BY_HASH.clear()
    l._TX_BY_KEY.clear()
    l._OPEN_BLOCK = None


def test_persist_and_replay_roundtrip(client: TestClient):
    from backend.modules.chain_sim import chain_sim_ledger as l

    # init DB on env-selected path
    l._db()

    # genesis
    r = client.post("/api/chain_sim/dev/reset", json={
        "chain_id": "glyphchain-dev",
        "network_id": "local",
        "allocs": [{"address": "pho1-s0", "balances": {"PHO": "10", "TESS": "0"}}],
        "validators": [],
    })
    assert r.status_code == 200, r.text

    # apply one tx
    r = client.post("/api/chain_sim/dev/submit_tx", json={
        "chain_id": "glyphchain-dev",
        "from_addr": "pho1-s0",
        "nonce": 0,
        "tx_type": "BANK_BURN",
        "payload": {"denom": "PHO", "amount": "1"},
    })
    assert r.status_code == 200, r.text
    assert r.json().get("applied") is True

    # verify tx persisted
    conn = l._db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(1) FROM txs")
    assert int(cur.fetchone()[0] or 0) >= 1

    # capture EXPECTED post-tx state (whatever the chain actually did)
    expected_supply = client.get("/api/chain_sim/dev/supply").json()
    expected_acct = client.get("/api/chain_sim/dev/account", params={"address": "pho1-s0"}).json()

    # simulate restart
    from backend.modules.chain_sim import chain_sim_config as cfg
    from backend.modules.chain_sim import chain_sim_model as bank
    from backend.modules.staking import staking_model as staking

    cfg.reset_config()
    staking.reset_state()
    bank.reset_state()
    _clear_ledger_only(l)

    assert l.replay_state_from_db() is True

    # must match the pre-restart snapshot exactly
    supply = client.get("/api/chain_sim/dev/supply").json()
    assert supply == expected_supply

    acct = client.get("/api/chain_sim/dev/account", params={"address": "pho1-s0"}).json()
    assert acct.get("balances") == expected_acct.get("balances")

    txs = client.get("/api/chain_sim/dev/txs?limit=50").json().get("txs") or []
    assert len(txs) >= 1