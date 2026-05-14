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
        assert r.status_code == 200
        last = r.json()
        st = (last.get("status") or {}).get("state") if isinstance(last.get("status"), dict) else None
        if st in ("finalized", "rejected", "error"):
            return last
        time.sleep(0.02)
    raise AssertionError(f"timeout waiting for qid={qid}: last={last}")


@pytest.mark.asyncio
async def test_chain_sim_blocks_pagination_and_ordering(monkeypatch):
    # force deterministic batching: 7 tx => 3 blocks (3,3,1)
    monkeypatch.setenv("CHAIN_SIM_ASYNC_ENABLED", "1")
    monkeypatch.setenv("CHAIN_SIM_BLOCK_MAX_TX", "3")
    monkeypatch.setenv("CHAIN_SIM_BLOCK_MAX_MS", "250")
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "off")
    monkeypatch.setenv("AION_ENABLE_COG_THREADS", "0")
    monkeypatch.setenv("AION_ENABLE_BOOT_LOADER", "0")
    monkeypatch.setenv("AION_ENABLE_HQCE", "0")
    monkeypatch.setenv("AION_ENABLE_GHX_TELEMETRY", "0")
    monkeypatch.setenv("AION_ENABLE_DUAL_HEARTBEAT", "0")

    import backend.main as main
    importlib.reload(main)

    with TestClient(main.app) as tc:
        _reset_chain_sim(tc)

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

        for qid in qids:
            st = _wait_finalized(tc, qid)
            assert (st.get("status") or {}).get("state") == "finalized", st

        # ---- full list: order=desc ----
        full_resp = tc.get(
            "/api/chain_sim/dev/blocks",
            params={"limit": 5000, "offset": 0, "order": "desc"},
        ).json()
        blocks_full = full_resp.get("blocks", full_resp)
        assert isinstance(blocks_full, list)

        heights_full = [int((b or {}).get("height") or 0) for b in blocks_full]
        assert len(heights_full) == 3
        assert heights_full == sorted(heights_full, reverse=True)  # newest first

        # ---- pagination: page 0 and page 1, order=desc ----
        blocks_resp = tc.get(
            "/api/chain_sim/dev/blocks",
            params={"limit": 2, "offset": 0, "order": "desc"},
        ).json()
        blocks0 = blocks_resp.get("blocks", blocks_resp)
        h0 = [int((b or {}).get("height") or 0) for b in blocks0]
        assert h0 == sorted(h0, reverse=True)
        assert len(h0) <= 2

        blocks_resp = tc.get(
            "/api/chain_sim/dev/blocks",
            params={"limit": 2, "offset": 2, "order": "desc"},
        ).json()
        blocks1 = blocks_resp.get("blocks", blocks_resp)
        h1 = [int((b or {}).get("height") or 0) for b in blocks1]
        assert h1 == sorted(h1, reverse=True)

        # pagination should not overlap
        assert set(h0).isdisjoint(set(h1))

        # paged concat should match the prefix of full ordering
        heights_paged = h0 + h1
        assert heights_paged == heights_full[: len(heights_paged)]