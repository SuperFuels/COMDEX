from __future__ import annotations

import importlib
import json
import os
import sqlite3
import time
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from backend.modules.chain_sim.chain_sim_merkle import hash_leaf, merkle_root


def _compute_txs_root_hex(tx_hashes: List[str]) -> str:
    leaves = []
    for h in tx_hashes:
        try:
            raw = bytes.fromhex(str(h))
        except Exception:
            raw = str(h).encode("utf-8")
        leaves.append(hash_leaf(raw))
    return merkle_root(leaves).hex()


def _extract_status(obj: Dict[str, Any]) -> str:
    """
    Normalize /tx_status/{qid} payloads across versions.

    IMPORTANT:
    - Do NOT treat presence of "error"/"detail"/"message" strings as failure by itself.
    - Prefer explicit success evidence (applied/tx_id/block_height/done_at_ms + not rejected).
    """
    # Some endpoints: {"status": "finalized"}
    v = obj.get("status")
    if isinstance(v, str):
        return v.strip().lower()

    # Some endpoints: {"state": "..."} or {"phase": "..."}
    for k in ("state", "phase"):
        vv = obj.get(k)
        if isinstance(vv, str):
            return vv.strip().lower()

    # Most common: {"ok": True, "status": {...}}
    if not isinstance(v, dict):
        return ""

    s = v

    # Sometimes the actual receipt is nested
    if isinstance(s.get("receipt"), dict):
        s = s["receipt"]  # type: ignore[assignment]

    # Explicit rejection signals
    if s.get("rejected") is True:
        return "rejected"
    if s.get("applied") is False:
        return "rejected"

    # Explicit success signals
    if s.get("applied") is True:
        return "finalized"

    for k in ("tx_id", "tx_hash", "block_height", "tx_index"):
        if s.get(k) not in (None, "", 0):
            return "finalized"

    # Explicit error signals (ONLY)
    if obj.get("ok") is False or s.get("ok") is False:
        return "error"

    for k in ("status", "state", "phase"):
        vv = s.get(k)
        if isinstance(vv, str):
            vv2 = vv.strip().lower()
            if vv2 in ("error", "failed", "exception"):
                return "error"
            if vv2 in ("rejected",):
                return "rejected"
            if vv2 in ("finalized", "committed", "applied", "done"):
                return "finalized"

    # If it completed, and we have no explicit rejection/error => treat as finalized
    if s.get("done_at_ms") is not None:
        return "finalized"

    return ""


def _wait_finalized(tc: TestClient, qid: str, timeout_s: float = 10.0) -> Dict[str, Any]:
    t0 = time.time()
    last: Dict[str, Any] = {}

    while time.time() - t0 < timeout_s:
        r = tc.get(f"/api/chain_sim/dev/tx_status/{qid}")
        assert r.status_code == 200
        last = r.json()

        st = last.get("status") or {}
        if isinstance(st, dict):
            phase = str(st.get("state") or st.get("phase") or st.get("status") or "").strip().lower()
            if phase in ("finalized", "rejected", "error", "failed", "fail"):
                return last

        time.sleep(0.02)

    raise AssertionError(f"timeout waiting for qid={qid}: last={last}")


def _reset_chain_sim(tc: TestClient) -> None:
    """
    Reset chain sim AND ensure pho1-alice is funded (PHO=10_000).
    Works across schema drift.
    """
    def _alice_pho() -> int:
        rr = tc.get("/api/chain_sim/dev/account", params={"address": "pho1-alice"})
        if rr.status_code != 200:
            return 0
        j = rr.json() or {}
        bals = (j.get("balances") or {}) if isinstance(j.get("balances"), dict) else {}
        try:
            return int(str(bals.get("PHO", "0")))
        except Exception:
            return 0

    # 1) try no-body reset (some servers seed defaults)
    r = tc.post("/api/chain_sim/dev/reset")
    if r.status_code == 200 and _alice_pho() >= 1:
        return

    # 2) canonical current schema (your DevResetRequest)
    r = tc.post(
        "/api/chain_sim/dev/reset",
        json={
            "chain_id": "glyphchain-dev",
            "network_id": "devnet",
            "allocs": [{"address": "pho1-alice", "balances": {"PHO": "10000"}}],
            "validators": [],
        },
    )
    if r.status_code == 200 and _alice_pho() >= 1:
        return

    # 3) older drift: config string + network_id
    r = tc.post(
        "/api/chain_sim/dev/reset",
        json={
            "config": "glyphchain-dev",
            "network_id": "devnet",
            "allocs": [{"address": "pho1-alice", "balances": {"PHO": "10000"}}],
            "validators": [],
        },
    )
    if r.status_code == 200 and _alice_pho() >= 1:
        return

    raise AssertionError(f"/dev/reset failed to fund alice: last={r.status_code} {r.text}")


def _norm_block(b: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize for stable equality:
      - keep only deterministic fields
      - sort txs by tx_index
    """
    hdr = (b.get("header") or {}) if isinstance(b.get("header"), dict) else {}
    txs = b.get("txs") or []
    if not isinstance(txs, list):
        txs = []

    txs_sorted = sorted(txs, key=lambda t: int((t or {}).get("tx_index") or 0))
    txs_norm: List[Dict[str, Any]] = []
    for t in txs_sorted:
        if not isinstance(t, dict):
            continue
        txs_norm.append(
            {
                "tx_id": t.get("tx_id"),
                "tx_hash": t.get("tx_hash"),
                "from_addr": t.get("from_addr"),
                "nonce": int(t.get("nonce") or 0),
                "tx_type": t.get("tx_type"),
                "payload": t.get("payload") if isinstance(t.get("payload"), dict) else {},
                "tx_index": int(t.get("tx_index") or 0),
            }
        )

    return {
        "height": int(b.get("height") or 0),
        "created_at_ms": int(b.get("created_at_ms") or 0),
        "txs_root": (hdr.get("txs_root") or b.get("txs_root") or ""),
        "state_root": (hdr.get("state_root") or ""),
        "txs": txs_norm,
    }


@pytest.mark.asyncio
async def test_chain_sim_persist_replay_commitments(tmp_path, monkeypatch):
    db_path = tmp_path / "chain_sim.sqlite3"

    # persistence + replay
    monkeypatch.setenv("CHAIN_SIM_PERSIST", "1")
    monkeypatch.setenv("CHAIN_SIM_REPLAY_ON_STARTUP", "1")
    monkeypatch.setenv("CHAIN_SIM_DB_PATH", str(db_path))

    # async batching to force multi-tx blocks deterministically
    monkeypatch.setenv("CHAIN_SIM_ASYNC_ENABLED", "1")
    monkeypatch.setenv("CHAIN_SIM_BLOCK_MAX_TX", "3")
    monkeypatch.setenv("CHAIN_SIM_BLOCK_MAX_MS", "250")

    # keep tests stable (force sig off so schema doesn't require pubkey/signature)
    monkeypatch.setenv("CHAIN_SIM_SIG_MODE", "off")
    monkeypatch.setenv("AION_ENABLE_COG_THREADS", "0")
    monkeypatch.setenv("AION_ENABLE_BOOT_LOADER", "0")
    monkeypatch.setenv("AION_ENABLE_HQCE", "0")
    monkeypatch.setenv("AION_ENABLE_GHX_TELEMETRY", "0")
    monkeypatch.setenv("AION_ENABLE_DUAL_HEARTBEAT", "0")

    import backend.main as main
    importlib.reload(main)

    root1: str | None = None
    blocks1_norm: List[Dict[str, Any]] = []

    with TestClient(main.app) as tc:
        _reset_chain_sim(tc)

        # submit 7 txs => blocks should be 3,3,1 under max_tx=3
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

        # IMPORTANT: wait for terminal status.state == finalized (not just receipt.applied)
        for qid in qids:
            st_payload = _wait_finalized(tc, qid)

            # strict: must be finalized (flush committed)
            assert (st_payload.get("status") or {}).get("state") == "finalized", st_payload

            st = st_payload.get("status") or {}
            receipt = st.get("receipt") or {}
            assert isinstance(receipt, dict), st_payload

            sr = receipt.get("state_root")
            tr = receipt.get("txs_root")
            assert isinstance(sr, str) and len(sr) == 64, st_payload
            assert isinstance(tr, str) and len(tr) == 64, st_payload
            assert receipt.get("state_root_committed") is True, st_payload

        state1 = tc.get("/api/chain_sim/dev/state").json()
        root1 = state1.get("state_root")
        assert isinstance(root1, str) and root1

        blocks_resp = tc.get("/api/chain_sim/dev/blocks").json()

        # handle both shapes: list or {"ok":True,"blocks":[...]}
        if isinstance(blocks_resp, dict) and isinstance(blocks_resp.get("blocks"), list):
            blocks1 = blocks_resp["blocks"]
        else:
            blocks1 = blocks_resp

        assert isinstance(blocks1, list)
        blocks1 = sorted(blocks1, key=lambda b: int((b or {}).get("height") or 0))
        assert len(blocks1) == 3

        # verify txs_root commitments per block
        for b in blocks1:
            txs = b.get("txs") or []
            tx_hashes = [t["tx_hash"] for t in txs]
            expect_root = _compute_txs_root_hex(tx_hashes)
            hdr = b.get("header") or {}
            got_root = (hdr.get("txs_root") or b.get("txs_root") or "")
            assert got_root == expect_root

        # last block's header.state_root should match /dev/state state_root
        last_hdr_root = ((blocks1[-1].get("header") or {}).get("state_root") or "")
        assert last_hdr_root == root1

        blocks1_norm = [_norm_block(b) for b in blocks1]

    # sanity: DB rows exist
    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM blocks;")
        nblocks = int(cur.fetchone()[0] or 0)
        assert nblocks == 3

        cur.execute("SELECT COUNT(*) FROM txs;")
        ntxs = int(cur.fetchone()[0] or 0)
        assert ntxs == 7
    finally:
        con.close()

    # "restart": reload app with same DB path; replay must reconstruct identical view
    import backend.main as main2
    importlib.reload(main2)

    with TestClient(main2.app) as tc2:
        state2 = tc2.get("/api/chain_sim/dev/state").json()
        root2 = state2.get("state_root")
        assert root2 == root1

        blocks2_resp = tc2.get("/api/chain_sim/dev/blocks").json()
        if isinstance(blocks2_resp, dict) and isinstance(blocks2_resp.get("blocks"), list):
            blocks2 = blocks2_resp["blocks"]
        else:
            blocks2 = blocks2_resp

        assert isinstance(blocks2, list)
        blocks2 = sorted(blocks2, key=lambda b: int((b or {}).get("height") or 0))
        blocks2_norm = [_norm_block(b) for b in blocks2]

        assert blocks2_norm == blocks1_norm