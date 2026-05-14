# backend/tests/test_chain_sim_receipts_roots_persisted.py
from __future__ import annotations

import importlib
import time
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient


def _reset_chain_sim(tc: TestClient) -> None:
    r = tc.post(
        "/api/chain_sim/dev/reset",
        json={
            "chain_id": "glyphchain-dev",
            "network_id": "devnet",
            "allocs": [{"address": "pho1-alice", "balances": {"PHO": "10000"}}],
            "validators": [],
        },
    )
    assert r.status_code == 200, r.text


def _wait_finalized(tc: TestClient, qid: str, timeout_s: float = 10.0) -> Dict[str, Any]:
    t0 = time.time()
    last: Dict[str, Any] = {}
    while time.time() - t0 < timeout_s:
        r = tc.get(f"/api/chain_sim/dev/tx_status/{qid}")
        assert r.status_code == 200, r.text
        last = r.json()
        st = (last.get("status") or {}).get("state") if isinstance(last.get("status"), dict) else None
        if st in ("finalized", "rejected", "error"):
            return last
        time.sleep(0.02)

    # extra debug on timeout (so it never “hangs silently”)
    qm = tc.get("/api/chain_sim/dev/queue_metrics").json()
    raise AssertionError(f"timeout waiting for qid={qid}: last={last} queue_metrics={qm}")


@pytest.mark.asyncio
async def test_chain_sim_receipts_roots_persisted_and_match_block(monkeypatch):
    # --- make the test deterministic + avoid “surprise” settings from your shell ---
    monkeypatch.setenv("CHAIN_SIM_ASYNC_ENABLED", "1")
    monkeypatch.setenv("CHAIN_SIM_BLOCK_MAX_TX", "3")     # 7 tx => 3 blocks (3,3,1)
    monkeypatch.setenv("CHAIN_SIM_BLOCK_MAX_MS", "250")
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "off")       # critical (no missing sig)
    monkeypatch.setenv("CHAIN_SIM_PERSIST", "1")          # we want persisted tx rows
    monkeypatch.setenv("CHAIN_SIM_REPLAY_ON_STARTUP", "0")
    monkeypatch.setenv("CHAIN_SIM_REPLAY_STRICT", "0")

    # turn off unrelated background systems that slow/hang tests
    monkeypatch.setenv("AION_ENABLE_COG_THREADS", "0")
    monkeypatch.setenv("AION_ENABLE_BOOT_LOADER", "0")
    monkeypatch.setenv("AION_ENABLE_HQCE", "0")
    monkeypatch.setenv("AION_ENABLE_GHX_TELEMETRY", "0")
    monkeypatch.setenv("AION_ENABLE_DUAL_HEARTBEAT", "0")

    import backend.main as main
    importlib.reload(main)

    with TestClient(main.app) as tc:
        _reset_chain_sim(tc)

        # submit 7 async txs
        qids: List[str] = []
        for i in range(7):
            rr = tc.post(
                "/api/chain_sim/dev/submit_tx_async",
                json={
                    "from_addr": "pho1-alice",
                    "nonce": i + 1,
                    "tx_type": "BANK_BURN",
                    "payload": {"denom": "PHO", "amount": 1},
                },
            )
            assert rr.status_code == 202, rr.text
            qids.append(rr.json()["qid"])

        # wait finalized and collect receipts
        receipts: List[Dict[str, Any]] = []
        for qid in qids:
            st = _wait_finalized(tc, qid, timeout_s=15.0)
            assert (st.get("status") or {}).get("state") == "finalized", st
            rec = (st.get("status") or {}).get("receipt") or {}
            receipts.append(rec)

        # for each finalized receipt:
        # 1) roots exist
        # 2) roots match /dev/block/{height}
        # 3) persisted /dev/tx/{tx_id} includes same roots
        for rec in receipts:
            assert rec.get("state_root_committed") is True, rec
            assert isinstance(rec.get("state_root"), str) and rec["state_root"], rec
            assert isinstance(rec.get("txs_root"), str) and rec["txs_root"], rec
            assert isinstance(rec.get("block_height"), int) and rec["block_height"] > 0, rec
            assert isinstance(rec.get("tx_id"), str) and rec["tx_id"], rec

            h = int(rec["block_height"])
            blk_resp = tc.get(f"/api/chain_sim/dev/block/{h}")
            assert blk_resp.status_code == 200, blk_resp.text
            blk = blk_resp.json()["block"]
            hdr = (blk or {}).get("header") or {}

            assert str(hdr.get("state_root") or "") == rec["state_root"], {"hdr": hdr, "rec": rec}
            assert str(hdr.get("txs_root") or "") == rec["txs_root"], {"hdr": hdr, "rec": rec}

            txid = rec["tx_id"]
            tx_resp = tc.get(f"/api/chain_sim/dev/tx/{txid}")
            assert tx_resp.status_code == 200, tx_resp.text
            tx = tx_resp.json()["tx"]

            # depending on your ledger shape, roots might live at top-level or inside receipt/result;
            # this makes the assertion robust while still strict.
            tx_state_root = str((tx or {}).get("state_root") or ((tx or {}).get("receipt") or {}).get("state_root") or "")
            tx_txs_root = str((tx or {}).get("txs_root") or ((tx or {}).get("receipt") or {}).get("txs_root") or "")
            tx_committed = (tx or {}).get("state_root_committed")
            if tx_committed is None:
                tx_committed = ((tx or {}).get("receipt") or {}).get("state_root_committed")

            assert tx_state_root == rec["state_root"], {"tx": tx, "rec": rec}
            assert tx_txs_root == rec["txs_root"], {"tx": tx, "rec": rec}
            assert tx_committed is True, {"tx": tx, "rec": rec}