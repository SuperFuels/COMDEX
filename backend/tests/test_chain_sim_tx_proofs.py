from __future__ import annotations

import os
import httpx

BASE = os.getenv("GLYPHCHAIN_URL") or os.getenv("CHAIN_SIM_URL") or "http://127.0.0.1:8080"
TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=5.0)


def _post(c: httpx.Client, path: str, json: dict) -> dict:
    r = c.post(f"{BASE}{path}", json=json)
    r.raise_for_status()
    return r.json()


def _get(c: httpx.Client, path: str, params: dict | None = None) -> dict:
    r = c.get(f"{BASE}{path}", params=params)
    r.raise_for_status()
    return r.json()


def test_tx_proof_roundtrip_and_height_binding():
    genesis = {
        "chain_id": "comdex-dev",
        "network_id": "local",
        "allocs": [
            {"address": "pho1-alice", "balances": {"PHO": "10", "TESS": "0"}},
            {"address": "pho1-bob", "balances": {"PHO": "0", "TESS": "0"}},
        ],
        "validators": [],
    }

    with httpx.Client(timeout=TIMEOUT) as c:
        _post(c, "/api/chain_sim/dev/reset", genesis)

        # tx1 (block 1)
        tx1 = _post(
            c,
            "/api/chain_sim/dev/submit_tx",
            {
                "from_addr": "pho1-alice",
                "nonce": 0,
                "tx_type": "BANK_SEND",
                "payload": {"denom": "PHO", "to": "pho1-bob", "amount": "1"},
            },
        )
        assert tx1.get("ok") is True
        assert tx1.get("applied") is True
        tx1_id = tx1.get("tx_id")
        assert isinstance(tx1_id, str) and tx1_id.startswith("tx_")
        h1 = int(tx1.get("block_height") or 0)
        assert h1 == 1

        proof1 = _get(c, "/api/chain_sim/dev/proof/tx", {"tx_id": tx1_id})
        assert proof1.get("ok") is True
        assert int(proof1.get("block_height") or 0) == 1
        assert proof1.get("tx_id") == tx1_id
        assert isinstance(proof1.get("txs_root"), str) and len(proof1["txs_root"]) == 64

        blk1 = _get(c, "/api/chain_sim/dev/block/1").get("block") or {}
        assert blk1.get("txs_root") == proof1["txs_root"]

        v1 = _post(
            c,
            "/api/chain_sim/dev/proof/verify_tx",
            {
                "tx_hash": proof1["tx_hash"],
                "txs_root": proof1["txs_root"],
                "proof": proof1["proof"],
            },
        )
        assert v1 == {"ok": True, "verified": True}

        # tx2 (block 2) — ensures proof endpoint binds to tx.block_height
        tx2 = _post(
            c,
            "/api/chain_sim/dev/submit_tx",
            {
                "from_addr": "pho1-alice",
                "nonce": 1,
                "tx_type": "BANK_SEND",
                "payload": {"denom": "PHO", "to": "pho1-bob", "amount": "1"},
            },
        )
        assert tx2.get("ok") is True
        assert tx2.get("applied") is True
        tx2_id = tx2.get("tx_id")
        h2 = int(tx2.get("block_height") or 0)
        assert h2 == 2

        proof2 = _get(c, "/api/chain_sim/dev/proof/tx", {"tx_id": tx2_id})
        assert proof2.get("ok") is True
        assert int(proof2.get("block_height") or 0) == 2

        blk2 = _get(c, "/api/chain_sim/dev/block/2").get("block") or {}
        assert blk2.get("txs_root") == proof2["txs_root"]

        v2 = _post(
            c,
            "/api/chain_sim/dev/proof/verify_tx",
            {
                "tx_hash": proof2["tx_hash"],
                "txs_root": proof2["txs_root"],
                "proof": proof2["proof"],
            },
        )
        assert v2 == {"ok": True, "verified": True}

        # re-check tx1 proof still points to block 1 (no accidental “latest root” usage)
        proof1_again = _get(c, "/api/chain_sim/dev/proof/tx", {"tx_id": tx1_id})
        assert int(proof1_again.get("block_height") or 0) == 1
        assert proof1_again.get("txs_root") == proof1["txs_root"]