# backend/tests/test_chain_sim_persist_replay.py
from __future__ import annotations

import importlib
import os
from typing import Any

import pytest
from fastapi.testclient import TestClient


def _get_json(tc: TestClient, path: str, **params) -> dict[str, Any]:
    r = tc.get(path, params=params or None)
    assert r.status_code == 200, r.text
    return r.json()


def _post_json(tc: TestClient, path: str, body: dict[str, Any]) -> dict[str, Any]:
    r = tc.post(path, json=body)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_chain_sim_persist_replay(tmp_path, monkeypatch):
    """
    Asserts:
      1) Persist enabled (sqlite) writes blocks/txs + genesis snapshot
      2) “Restart” (reload backend.main) with same DB replays state deterministically
      3) /dev/state state_root matches, and blocks/txs returned match exactly
    """
    db_path = tmp_path / "chain_sim_replay.sqlite3"

    # --- env for BOTH runs (must be set before importing backend.main) ---
    monkeypatch.setenv("CHAIN_SIM_PERSIST", "1")
    monkeypatch.setenv("CHAIN_SIM_DB_PATH", str(db_path))
    monkeypatch.setenv("CHAIN_SIM_REPLAY_ON_STARTUP", "1")

    # Keep it deterministic + simple for the test
    monkeypatch.setenv("CHAIN_SIM_ASYNC_ENABLED", "0")
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "off")
    monkeypatch.setenv("CHAIN_SIM_BLOCK_MAX_TX", "100")
    monkeypatch.setenv("CHAIN_SIM_BLOCK_MAX_MS", "25")

    # keep startup light in pytest
    monkeypatch.setenv("AION_ENABLE_DUAL_HEARTBEAT", "0")
    monkeypatch.setenv("AION_ENABLE_HQCE", "0")
    monkeypatch.setenv("AION_ENABLE_GHX_TELEMETRY", "0")
    monkeypatch.setenv("AION_ENABLE_BOOT_LOADER", "0")
    monkeypatch.setenv("AION_ENABLE_SCHEDULER", "0")
    monkeypatch.setenv("AION_SEED_PATTERNS", "0")

    # ---------------- run #1: create genesis + tx log ----------------
    import backend.main as main
    importlib.reload(main)

    with TestClient(main.app) as tc:
        base = "/api"
        sender = "pho1-s0"
        genesis = {
            "chain_id": "glyphchain-dev",
            "network_id": "local",
            "allocs": [{"address": sender, "balances": {"PHO": "1000000", "TESS": "0"}}],
            "validators": [],
        }
        _post_json(tc, f"{base}/chain_sim/dev/reset", genesis)

        acct0 = _get_json(tc, f"{base}/chain_sim/dev/account", address=sender)
        nonce0 = int(acct0.get("nonce", 0))

        # small deterministic tx sequence
        for i in range(10):
            tx = {
                "chain_id": "glyphchain-dev",
                "from_addr": sender,
                "nonce": nonce0 + i,
                "tx_type": "BANK_BURN",
                "payload": {"denom": "PHO", "amount": "1"},
            }
            r = tc.post(f"{base}/chain_sim/dev/submit_tx", json=tx)
            assert r.status_code == 200, r.text
            j = r.json()
            assert j.get("applied") is True, j

        st1 = _get_json(tc, f"{base}/chain_sim/dev/state")
        root1 = st1.get("state_root")
        assert isinstance(root1, str) and root1

        blocks1 = _get_json(tc, f"{base}/chain_sim/dev/blocks", limit=500, offset=0).get("blocks") or []
        txs1 = _get_json(tc, f"{base}/chain_sim/dev/txs", limit=500, offset=0).get("txs") or []

    # ---------------- run #2: “restart” and replay from same DB ----------------
    importlib.reload(main)

    with TestClient(main.app) as tc2:
        st2 = _get_json(tc2, "/api/chain_sim/dev/state")
        root2 = st2.get("state_root")
        assert root2 == root1

        blocks2 = _get_json(tc2, "/api/chain_sim/dev/blocks", limit=500, offset=0).get("blocks") or []
        txs2 = _get_json(tc2, "/api/chain_sim/dev/txs", limit=500, offset=0).get("txs") or []

        assert blocks2 == blocks1
        assert txs2 == txs1