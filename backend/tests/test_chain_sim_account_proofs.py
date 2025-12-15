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


def test_chain_sim_dev_account_proof_and_verify():
    genesis = {
        "chain_id": "comdex-dev",
        "network_id": "local",
        "allocs": [
            {"address": "addr1", "balances": {"PHO": "10", "TESS": "10"}},
            {"address": "addr2", "balances": {"PHO": "0", "TESS": "0"}},
        ],
        "validators": [],
    }

    with httpx.Client(timeout=TIMEOUT) as c:
        _post(c, "/api/chain_sim/dev/reset", genesis)

        # mutate state once (so we're not only proving genesis)
        a1 = _get(c, "/api/chain_sim/dev/account", {"address": "addr1"})
        send = _post(
            c,
            "/api/chain_sim/dev/submit_tx",
            {
                "from_addr": "addr1",
                "nonce": int(a1.get("nonce", 0)),
                "tx_type": "BANK_SEND",
                "payload": {"denom": "TESS", "to": "addr2", "amount": "1"},
            },
        )
        assert send.get("ok") is True
        assert send.get("applied") is True

        # 3) GET /dev/state (grab state_root + committed bank root)
        st = _get(c, "/api/chain_sim/dev/state")
        assert st.get("ok") is True
        assert isinstance(st.get("state_root"), str) and len(st["state_root"]) == 64

        state = st.get("state") or {}
        assert isinstance(state, dict)
        bank = (state.get("bank") or {})
        assert isinstance(bank, dict)
        committed_root = bank.get("root")
        assert isinstance(committed_root, str) and len(committed_root) == 64

        # 4) GET /dev/proof/account?address=...
        proof = _get(c, "/api/chain_sim/dev/proof/account", {"address": "addr1"})
        assert proof.get("ok") is True
        assert proof.get("algo") == "sha256-merkle-v1"
        assert isinstance(proof.get("bank_accounts_root"), str) and len(proof["bank_accounts_root"]) == 64
        assert isinstance(proof.get("proof"), list)
        assert isinstance(proof.get("leaf_hash"), str) and len(proof["leaf_hash"]) == 64
        assert isinstance(proof.get("account"), dict)
        assert proof["account"].get("address") == "addr1"

        # committed root must match proof root
        assert proof.get("bank_accounts_root") == committed_root

        # 5) POST verify (using leaf_hash)
        v = _post(
            c,
            "/api/chain_sim/dev/proof/verify_account",
            {
                "bank_accounts_root": proof["bank_accounts_root"],
                "proof": proof["proof"],
                "leaf_hash": proof["leaf_hash"],
            },
        )
        assert v.get("ok") is True
        assert v.get("verified") is True

        # negative: tamper the account payload and verify via {account:...}
        bad_account = dict(proof["account"])
        bad_account["nonce"] = int(bad_account.get("nonce", 0)) + 1

        v2 = _post(
            c,
            "/api/chain_sim/dev/proof/verify_account",
            {
                "bank_accounts_root": proof["bank_accounts_root"],
                "proof": proof["proof"],
                "account": bad_account,
            },
        )
        assert v2.get("ok") is True
        assert v2.get("verified") is False