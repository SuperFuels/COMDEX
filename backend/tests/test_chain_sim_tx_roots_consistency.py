# backend/tests/test_chain_sim_tx_roots_consistency.py
from __future__ import annotations

import faulthandler
import importlib
import sys
import time
from typing import Any, Dict, List

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _p(*a: Any) -> None:
    print(*a, flush=True)


def _reset_chain_sim(tc: TestClient) -> None:
    _p("[test] POST /dev/reset")
    r = tc.post(
        "/api/chain_sim/dev/reset",
        json={"chain_id": "glyphchain-dev", "network_id": "devnet"},
    )
    _p("[test] reset status", r.status_code)
    assert r.status_code == 200, r.text


def _wait_finalized(tc: TestClient, qid: str, timeout_s: float = 10.0) -> Dict[str, Any]:
    _p(f"[test] wait_finalized qid={qid}")
    t0 = time.time()
    last: Dict[str, Any] = {}
    next_report = t0 + 1.0

    while time.time() - t0 < timeout_s:
        r = tc.get(f"/api/chain_sim/dev/tx_status/{qid}")
        assert r.status_code == 200, r.text
        last = r.json()

        st = (last.get("status") or {}).get("state") if isinstance(last.get("status"), dict) else None
        if st in ("finalized", "rejected", "error"):
            _p(f"[test] qid={qid} terminal state={st}")
            return last

        now = time.time()
        if now >= next_report:
            try:
                qm = tc.get("/api/chain_sim/dev/queue_metrics").json()
            except Exception as e:
                qm = {"error": repr(e)}
            _p(f"[test] qid={qid} still waiting... state={st} queue_metrics={qm}")
            next_report = now + 1.0

        time.sleep(0.02)

    try:
        qm = tc.get("/api/chain_sim/dev/queue_metrics").json()
    except Exception as e:
        qm = {"error": repr(e)}

    raise AssertionError(f"timeout waiting for qid={qid}: last={last} queue_metrics={qm}")


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_chain_sim_tx_roots_consistency(monkeypatch, tmp_path):
    # If we hang anywhere > 20s, dump full stacks of all threads
    faulthandler.dump_traceback_later(20, repeat=True, file=sys.stderr)

    _p("[test] setting env")
    monkeypatch.setenv("CHAIN_SIM_ASYNC_ENABLED", "1")
    monkeypatch.setenv("CHAIN_SIM_BLOCK_MAX_TX", "3")
    monkeypatch.setenv("CHAIN_SIM_BLOCK_MAX_MS", "250")
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "off")

    # isolate DB so replay/startup can't touch shared repo db
    monkeypatch.setenv("CHAIN_SIM_PERSIST", "1")
    monkeypatch.setenv("CHAIN_SIM_DB_PATH", str(tmp_path / "chain_sim.sqlite3"))

    # kill boot noise / background processes (AION zoo)
    monkeypatch.setenv("AION_ENABLE_DUAL_HEARTBEAT", "0")
    monkeypatch.setenv("AION_ENABLE_SCHEDULER", "0")
    monkeypatch.setenv("AION_ENABLE_BOOT_LOADER", "0")
    monkeypatch.setenv("AION_ENABLE_COG_THREADS", "0")
    monkeypatch.setenv("AION_ENABLE_HQCE", "0")
    monkeypatch.setenv("AION_ENABLE_GHX_TELEMETRY", "0")
    monkeypatch.setenv("AION_ENABLE_PHI_BALANCE", "0")
    monkeypatch.setenv("AION_SEED_PATTERNS", "0")

    # SQI kills (safe even if unused)
    monkeypatch.setenv("SQI_ENABLE", "0")
    monkeypatch.setenv("SQI_HARDWARE_MODE", "0")
    monkeypatch.setenv("SQI_FORCE_HARDWARE", "0")
    monkeypatch.setenv("SQI_FORCE_GPIO", "0")
    monkeypatch.setenv("SQI_HEARTBEAT_ENABLE", "0")

    _p("[test] importing engine/routes")
    import backend.modules.chain_sim.chain_sim_engine as engine
    import backend.modules.chain_sim.chain_sim_routes as routes

    _p("[test] reload engine/routes")
    importlib.reload(engine)
    importlib.reload(routes)

    app = FastAPI()
    app.include_router(routes.router, prefix="/api")

    @app.on_event("startup")
    async def _startup():
        _p("[lifespan] startup begin")
        await routes.chain_sim_replay_startup()
        _p("[lifespan] replay_startup done")
        await routes.chain_sim_async_startup()
        _p("[lifespan] async_startup done")

    @app.on_event("shutdown")
    async def _shutdown():
        _p("[lifespan] shutdown begin")
        await routes.chain_sim_async_shutdown()
        _p("[lifespan] shutdown done")

    _p("[test] entering TestClient context (this is where startup can hang)")
    with TestClient(app) as tc:
        _p("[test] TestClient entered OK")

        # quick “is router alive?”
        r = tc.get("/api/chain_sim/dev/config")
        _p("[test] GET /dev/config", r.status_code)

        _reset_chain_sim(tc)

        # submit 7 async txs
        qids: List[str] = []
        for nonce in range(1, 8):
            rr = tc.post(
                "/api/chain_sim/dev/submit_tx_async",
                json={
                    "from_addr": engine.DEV_MINT_AUTHORITY,
                    "nonce": nonce,
                    "tx_type": "BANK_MINT",
                    "payload": {"denom": "PHO", "to": f"pho1-user{nonce}", "amount": "2"},
                    "chain_id": "glyphchain-dev",
                },
            )
            _p("[test] submit status", rr.status_code, "nonce", nonce, "body", rr.text[:200])
            assert rr.status_code == 202, rr.text
            qids.append(rr.json()["qid"])

        _p("[test] qids =", qids)

        for qid in qids:
            last = _wait_finalized(tc, qid)
            st = last["status"]
            assert st["state"] == "finalized", last

            receipt = st["receipt"]
            tx_id = receipt["tx_id"]
            height = int(receipt["block_height"])
            receipt_state_root = receipt["state_root"]
            receipt_txs_root = receipt["txs_root"]

            assert receipt.get("state_root_committed") is True

            blk = tc.get(f"/api/chain_sim/dev/block/{height}").json()["block"]
            assert blk["header"]["state_root"] == receipt_state_root
            assert blk["header"]["txs_root"] == receipt_txs_root

            tx = tc.get(f"/api/chain_sim/dev/tx/{tx_id}").json()["tx"]
            assert tx["result"]["state_root"] == receipt_state_root
            assert tx["result"]["txs_root"] == receipt_txs_root
            assert tx["result"]["state_root_committed"] is True

    _p("[test] exited TestClient context (shutdown ran)")