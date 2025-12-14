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


def _latest_height(c: httpx.Client) -> int:
    r = c.get(f"{BASE}/api/chain_sim/dev/blocks", params={"limit": 1, "offset": 0})
    r.raise_for_status()
    blocks = r.json().get("blocks") or []
    return int(blocks[0]["height"]) if blocks else 0


def test_bank_mint_send_burn_and_nonce_rules():
    genesis = {
        "chain_id": "comdex-dev",
        "network_id": "local",
        "allocs": [
            {"address": "addr1", "balances": {"PHO": "0", "TESS": "0"}},
            {"address": "addr2", "balances": {"PHO": "0", "TESS": "0"}},
        ],
        "validators": [],
    }

    with httpx.Client(timeout=TIMEOUT) as c:
        # reset
        _post(c, "/api/chain_sim/dev/reset", genesis)

        # 1) BANK_MINT: +balance(to) +supply, nonce increments on signer only
        mint = _post(
            c,
            "/api/chain_sim/dev/submit_tx",
            {
                "from_addr": "DEV_MINT_AUTHORITY",
                "nonce": 0,
                "tx_type": "BANK_MINT",
                "payload": {"denom": "TESS", "to": "addr1", "amount": "10"},
            },
        )
        assert mint.get("ok") is True
        assert mint.get("applied") is True
        assert mint.get("block_height") == 1
        assert isinstance(mint.get("state_root"), str) and len(mint["state_root"]) == 64

        # block header commits state_root
        blk1 = _get(c, "/api/chain_sim/dev/block/1").get("block") or {}
        assert (blk1.get("header") or {}).get("state_root") == mint["state_root"]

        a1 = _get(c, "/api/chain_sim/dev/account", {"address": "addr1"})
        assert a1["balances"].get("TESS") == "10"
        assert int(a1["nonce"]) == 0

        supply = _get(c, "/api/chain_sim/dev/supply")
        assert supply.get("TESS") == "10"

        auth = _get(c, "/api/chain_sim/dev/account", {"address": "DEV_MINT_AUTHORITY"})
        assert int(auth["nonce"]) == 1  # signer nonce increments

        # 2) BANK_SEND: moves balance, preserves total supply, nonce increments on sender
        send = _post(
            c,
            "/api/chain_sim/dev/submit_tx",
            {
                "from_addr": "addr1",
                "nonce": 0,
                "tx_type": "BANK_SEND",
                "payload": {"denom": "TESS", "to": "addr2", "amount": "3"},
            },
        )
        assert send.get("ok") is True
        assert send.get("applied") is True

        a1 = _get(c, "/api/chain_sim/dev/account", {"address": "addr1"})
        a2 = _get(c, "/api/chain_sim/dev/account", {"address": "addr2"})
        supply = _get(c, "/api/chain_sim/dev/supply")

        assert a1["balances"].get("TESS") == "7"
        assert int(a1["nonce"]) == 1
        assert a2["balances"].get("TESS") == "3"
        assert supply.get("TESS") == "10"  # unchanged

        # 3) BANK_BURN: -balance(from) -supply, nonce increments on signer
        burn = _post(
            c,
            "/api/chain_sim/dev/submit_tx",
            {
                "from_addr": "addr1",
                "nonce": 1,
                "tx_type": "BANK_BURN",
                "payload": {"denom": "TESS", "amount": "2"},
            },
        )
        assert burn.get("ok") is True
        assert burn.get("applied") is True

        a1 = _get(c, "/api/chain_sim/dev/account", {"address": "addr1"})
        supply = _get(c, "/api/chain_sim/dev/supply")

        assert a1["balances"].get("TESS") == "5"
        assert int(a1["nonce"]) == 2
        assert supply.get("TESS") == "8"

        # 4) Bad nonce rejected (no mutation, no new block)
        before_h = _latest_height(c)
        before_a1 = _get(c, "/api/chain_sim/dev/account", {"address": "addr1"})
        before_a2 = _get(c, "/api/chain_sim/dev/account", {"address": "addr2"})
        before_supply = _get(c, "/api/chain_sim/dev/supply")

        bad = _post(
            c,
            "/api/chain_sim/dev/submit_tx",
            {
                "from_addr": "addr1",
                "nonce": 999,
                "tx_type": "BANK_SEND",
                "payload": {"denom": "TESS", "to": "addr2", "amount": "1"},
            },
        )
        assert bad.get("ok") is False
        assert bad.get("applied") is False
        assert "bad nonce" in (bad.get("error") or "")

        after_a1 = _get(c, "/api/chain_sim/dev/account", {"address": "addr1"})
        after_a2 = _get(c, "/api/chain_sim/dev/account", {"address": "addr2"})
        after_supply = _get(c, "/api/chain_sim/dev/supply")
        after_h = _latest_height(c)

        assert after_a1 == before_a1
        assert after_a2 == before_a2
        assert after_supply == before_supply
        assert after_h == before_h