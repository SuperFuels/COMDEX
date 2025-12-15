from __future__ import annotations

import os
import httpx


BASE = os.getenv("GLYPHCHAIN_URL") or os.getenv("CHAIN_SIM_URL") or "http://127.0.0.1:8080"
TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=5.0)

FEE_COLLECTOR = "pho1-dev-fee-collector"


def _post(c: httpx.Client, path: str, json: dict) -> dict:
    r = c.post(f"{BASE}{path}", json=json)
    r.raise_for_status()
    return r.json()


def _get(c: httpx.Client, path: str, params: dict | None = None) -> dict:
    r = c.get(f"{BASE}{path}", params=params)
    r.raise_for_status()
    return r.json()


def _latest_height(c: httpx.Client) -> int:
    j = _get(c, "/api/chain_sim/dev/blocks", {"limit": 1, "offset": 0})
    blocks = j.get("blocks") or []
    return int(blocks[0]["height"]) if blocks else 0


def _latest_block(c: httpx.Client) -> dict:
    j = _get(c, "/api/chain_sim/dev/blocks", {"limit": 1, "offset": 0})
    blocks = j.get("blocks") or []
    assert blocks, "expected at least 1 block"
    blk = blocks[0]
    assert isinstance(blk, dict)
    return blk


def test_chain_sim_dev_fees_send_burn_mint_and_rejects():
    genesis = {
        "chain_id": "comdex-dev",
        "network_id": "local",
        "allocs": [
            # fund alice with PHO for fees and some TESS for non-fee transfers
            {"address": "addr1", "balances": {"PHO": "10", "TESS": "10"}},
            {"address": "addr2", "balances": {"PHO": "0", "TESS": "0"}},
            {"address": FEE_COLLECTOR, "balances": {"PHO": "0", "TESS": "0"}},
        ],
        "validators": [],
    }

    with httpx.Client(timeout=TIMEOUT) as c:
        _post(c, "/api/chain_sim/dev/reset", genesis)

        # 1) SEND charges 1 PHO from signer and credits collector
        pre_a1 = _get(c, "/api/chain_sim/dev/account", {"address": "addr1"})
        pre_col = _get(c, "/api/chain_sim/dev/account", {"address": FEE_COLLECTOR})
        pre_h = _latest_height(c)

        send = _post(
            c,
            "/api/chain_sim/dev/submit_tx",
            {
                "from_addr": "addr1",
                "nonce": int(pre_a1["nonce"]),
                "tx_type": "BANK_SEND",
                "payload": {"denom": "TESS", "to": "addr2", "amount": "1"},
            },
        )
        assert send.get("ok") is True
        assert send.get("applied") is True
        assert isinstance((send.get("result") or {}).get("fee"), dict)

        post_a1 = _get(c, "/api/chain_sim/dev/account", {"address": "addr1"})
        post_col = _get(c, "/api/chain_sim/dev/account", {"address": FEE_COLLECTOR})
        post_h = _latest_height(c)

        assert post_h == pre_h + 1
        assert int(post_a1["balances"].get("PHO", "0")) == int(pre_a1["balances"].get("PHO", "0")) - 1
        assert int(post_col["balances"].get("PHO", "0")) == int(pre_col["balances"].get("PHO", "0")) + 1

        # Ensure the applied tx was recorded in the newest block and fee persisted to ledger tx record
        blk = _latest_block(c)
        assert int(blk.get("height") or 0) == int(send.get("block_height") or 0)
        txs = blk.get("txs") or []
        assert txs and isinstance(txs[0], dict)
        assert isinstance(txs[0].get("fee"), dict)
        assert txs[0]["fee"].get("denom") == "PHO"
        assert txs[0]["fee"].get("amount") == "1"

        # 2) BURN charges 1 PHO
        pre_a1 = post_a1
        pre_col = post_col
        burn = _post(
            c,
            "/api/chain_sim/dev/submit_tx",
            {
                "from_addr": "addr1",
                "nonce": int(pre_a1["nonce"]),
                "tx_type": "BANK_BURN",
                "payload": {"denom": "TESS", "amount": "1"},
            },
        )
        assert burn.get("ok") is True
        assert burn.get("applied") is True
        assert isinstance((burn.get("result") or {}).get("fee"), dict)

        post_a1 = _get(c, "/api/chain_sim/dev/account", {"address": "addr1"})
        post_col = _get(c, "/api/chain_sim/dev/account", {"address": FEE_COLLECTOR})

        assert int(post_a1["balances"].get("PHO", "0")) == int(pre_a1["balances"].get("PHO", "0")) - 1
        assert int(post_col["balances"].get("PHO", "0")) == int(pre_col["balances"].get("PHO", "0")) + 1

        # 3) MINT(PHO) carves out correctly: recipient gets amount-1, collector gets 1
        mint_auth = _get(c, "/api/chain_sim/dev/account", {"address": "DEV_MINT_AUTHORITY"})
        pre_to = _get(c, "/api/chain_sim/dev/account", {"address": "addr2"})
        pre_col = _get(c, "/api/chain_sim/dev/account", {"address": FEE_COLLECTOR})

        mint = _post(
            c,
            "/api/chain_sim/dev/submit_tx",
            {
                "from_addr": "DEV_MINT_AUTHORITY",
                "nonce": int(mint_auth["nonce"]),
                "tx_type": "BANK_MINT",
                "payload": {"denom": "PHO", "to": "addr2", "amount": "5"},
            },
        )
        assert mint.get("ok") is True
        assert mint.get("applied") is True
        fee = (mint.get("result") or {}).get("fee")
        assert isinstance(fee, dict)
        assert fee.get("mode") == "mint_carveout"
        assert fee.get("denom") == "PHO"
        assert fee.get("amount") == "1"

        post_to = _get(c, "/api/chain_sim/dev/account", {"address": "addr2"})
        post_col = _get(c, "/api/chain_sim/dev/account", {"address": FEE_COLLECTOR})

        # addr2 PHO increased by 4 (5-1)
        assert int(post_to["balances"].get("PHO", "0")) == int(pre_to["balances"].get("PHO", "0")) + 4
        # collector PHO increased by 1
        assert int(post_col["balances"].get("PHO", "0")) == int(pre_col["balances"].get("PHO", "0")) + 1

        # 4) bad fee balance rejects tx with ok=True, applied=False and no new block
        genesis2 = {
            "chain_id": "comdex-dev",
            "network_id": "local",
            "allocs": [
                {"address": "addrX", "balances": {"PHO": "0", "TESS": "10"}},  # no PHO for fee
                {"address": "addrY", "balances": {"PHO": "0", "TESS": "0"}},
                {"address": FEE_COLLECTOR, "balances": {"PHO": "0", "TESS": "0"}},
            ],
            "validators": [],
        }
        _post(c, "/api/chain_sim/dev/reset", genesis2)

        pre_h = _latest_height(c)
        pre_x = _get(c, "/api/chain_sim/dev/account", {"address": "addrX"})

        bad = _post(
            c,
            "/api/chain_sim/dev/submit_tx",
            {
                "from_addr": "addrX",
                "nonce": int(pre_x["nonce"]),
                "tx_type": "BANK_SEND",
                "payload": {"denom": "TESS", "to": "addrY", "amount": "1"},
            },
        )
        assert bad.get("ok") is True
        assert bad.get("applied") is False
        assert "tx_id" not in bad
        assert "tx_hash" not in bad
        assert "block_height" not in bad
        assert "tx_index" not in bad
        assert "state_root" not in bad

        post_h = _latest_height(c)
        assert post_h == pre_h