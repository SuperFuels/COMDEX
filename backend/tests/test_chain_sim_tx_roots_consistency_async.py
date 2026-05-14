from __future__ import annotations

import importlib
import time
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _reset_chain_sim(tc: TestClient) -> None:
    r = tc.post(
        "/api/chain_sim/dev/reset",
        json={"chain_id": "glyphchain-dev", "network_id": "devnet"},
    )
    assert r.status_code == 200, r.text


def _wait_terminal(tc: TestClient, qid: str, timeout_s: float = 10.0) -> Dict[str, Any]:
    t0 = time.time()
    last: Dict[str, Any] = {}
    while time.time() - t0 < timeout_s:
        r = tc.get(f"/api/chain_sim/dev/tx_status/{qid}")
        assert r.status_code == 200, r.text
        last = r.json()

        st = last.get("status") if isinstance(last.get("status"), dict) else {}
        state = st.get("state")
        if state in ("finalized", "rejected", "error"):
            return last

        time.sleep(0.02)

    qm = tc.get("/api/chain_sim/dev/queue_metrics").json()
    raise AssertionError(f"timeout waiting terminal qid={qid}: last={last} queue_metrics={qm}")


def test_async_roots_consistent_across_status_block_tx(monkeypatch):
    # --- env first (before imports) ---
    monkeypatch.setenv("CHAIN_SIM_ASYNC_ENABLED", "1")
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "off")
    monkeypatch.setenv("CHAIN_SIM_BLOCK_MAX_TX", "3")
    monkeypatch.setenv("CHAIN_SIM_BLOCK_MAX_MS", "250")
    monkeypatch.setenv("CHAIN_SIM_PERSIST", "1")

    # kill boot noise / background processes
    monkeypatch.setenv("AION_ENABLE_DUAL_HEARTBEAT", "0")
    monkeypatch.setenv("AION_ENABLE_SCHEDULER", "0")
    monkeypatch.setenv("AION_ENABLE_BOOT_LOADER", "0")
    monkeypatch.setenv("AION_ENABLE_COG_THREADS", "0")
    monkeypatch.setenv("AION_ENABLE_HQCE", "0")
    monkeypatch.setenv("AION_ENABLE_GHX_TELEMETRY", "0")
    monkeypatch.setenv("AION_SEED_PATTERNS", "0")

    # if you have SQI flags, disable those too (best-effort, harmless if unused)
    monkeypatch.setenv("SQI_HARDWARE_MODE", "0")
    monkeypatch.setenv("SQI_ENABLE", "0")

    # --- import AFTER env; reload to force env to be re-read ---
    import backend.modules.chain_sim.chain_sim_engine as engine
    import backend.modules.chain_sim.chain_sim_routes as routes

    importlib.reload(engine)
    importlib.reload(routes)

    app = FastAPI()
    app.include_router(routes.router, prefix="/api")

    @app.on_event("startup")
    async def _startup():
        await routes.chain_sim_replay_startup()
        await routes.chain_sim_async_startup()

    @app.on_event("shutdown")
    async def _shutdown():
        await routes.chain_sim_async_shutdown()

    with TestClient(app) as tc:
        _reset_chain_sim(tc)

        # submit 7 async txs (force multiple blocks with max_tx=3)
        qids: List[str] = []
        for nonce in range(1, 8):
            rr = tc.post(
                "/api/chain_sim/dev/submit_tx_async",
                json={
                    "from_addr": engine.DEV_MINT_AUTHORITY,
                    "nonce": nonce,
                    "tx_type": "BANK_MINT",
                    "payload": {"denom": "PHO", "to": f"pho1-user{nonce}", "amount": "1"},
                    "chain_id": "glyphchain-dev",
                },
            )
            assert rr.status_code == 202, rr.text
            qids.append(rr.json()["qid"])

        # verify consistency for each finalized tx
        for qid in qids:
            last = _wait_terminal(tc, qid)
            st = last["status"]
            assert st["state"] == "finalized", last

            receipt = st.get("receipt") or {}
            assert receipt.get("state_root_committed") is True, receipt

            receipt_state_root = receipt.get("state_root")
            receipt_txs_root = receipt.get("txs_root")
            tx_id = receipt.get("tx_id")
            height = receipt.get("block_height")

            assert isinstance(receipt_state_root, str) and receipt_state_root
            assert isinstance(receipt_txs_root, str) and receipt_txs_root
            assert isinstance(tx_id, str) and tx_id
            assert isinstance(height, int) and height > 0

            # (1) tx explorer record uses tx["result"][...]
            tx = tc.get(f"/api/chain_sim/dev/tx/{tx_id}").json()["tx"]
            assert tx["result"]["state_root"] == receipt_state_root
            assert tx["result"]["txs_root"] == receipt_txs_root
            assert tx["result"]["state_root_committed"] is True

            # (2) block header roots must match
            blk = tc.get(f"/api/chain_sim/dev/block/{height}").json()["block"]
            assert blk["header"]["state_root"] == receipt_state_root
            assert blk["header"]["txs_root"] == receipt_txs_root