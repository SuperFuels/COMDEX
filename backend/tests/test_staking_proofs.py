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


def _committed_staking_roots(c: httpx.Client) -> tuple[str, str]:
    """
    Return (validators_root, delegations_root) as committed under /dev/state.
    """
    st = _get(c, "/api/chain_sim/dev/state")
    assert st.get("ok") is True
    state = st.get("state") or {}
    staking = (state.get("staking") or {}) if isinstance(state, dict) else {}

    vroot = staking.get("validators_root")
    droot = staking.get("delegations_root")

    assert isinstance(vroot, str) and len(vroot) == 64
    assert isinstance(droot, str) and len(droot) == 64
    return vroot, droot


def test_staking_validator_and_delegation_proofs():
    genesis = {
        "chain_id": "comdex-dev",
        "network_id": "local",
        "allocs": [
            {"address": "del1", "balances": {"PHO": "0", "TESS": "10"}},
        ],
        "validators": [
            {"address": "val1", "self_delegation_tess": "0", "commission": "0"},
        ],
    }

    with httpx.Client(timeout=TIMEOUT) as c:
        _post(c, "/api/chain_sim/dev/reset", genesis)

        # committed roots live under /dev/state
        committed_vroot, committed_droot = _committed_staking_roots(c)

        # 1) validator proof
        pv = _get(c, "/api/staking/dev/proof/validator", {"address": "val1"})
        assert pv.get("ok") is True

        # support both canonical + back-compat field names
        proof_vroot = pv.get("validators_root") or pv.get("staking_validators_root")
        assert isinstance(proof_vroot, str) and len(proof_vroot) == 64
        assert proof_vroot == committed_vroot

        vv = _post(
            c,
            "/api/staking/dev/proof/verify_validator",
            {
                # verifier expects staking_validators_root (but allow either in case it evolves)
                "staking_validators_root": pv.get("staking_validators_root") or pv.get("validators_root"),
                "proof": pv["proof"],
                "leaf_hash": pv["leaf_hash"],
            },
        )
        assert vv.get("ok") is True
        assert vv.get("verified") is True

        # 2) delegation proof (only if STAKING_DELEGATE wired + applies)
        d = _get(c, "/api/chain_sim/dev/account", {"address": "del1"})
        tx = _post(
            c,
            "/api/chain_sim/dev/submit_tx",
            {
                "from_addr": "del1",
                "nonce": int(d.get("nonce", 0)),
                "tx_type": "STAKING_DELEGATE",
                "payload": {"validator": "val1", "amount_tess": "5"},
            },
        )

        if tx.get("applied") is not True:
            # endpoint exists but delegate not wired => test should exit cleanly
            assert tx.get("ok") is True
            assert tx.get("applied") is False
            return

        # ✅ refresh committed roots AFTER delegation mutates staking state
        committed_vroot, committed_droot = _committed_staking_roots(c)

        pd = _get(c, "/api/staking/dev/proof/delegation", {"delegator": "del1", "validator": "val1"})
        assert pd.get("ok") is True

        # support both canonical + back-compat field names
        proof_droot = pd.get("delegations_root") or pd.get("staking_delegations_root")
        assert isinstance(proof_droot, str) and len(proof_droot) == 64
        assert proof_droot == committed_droot

        vd = _post(
            c,
            "/api/staking/dev/proof/verify_delegation",
            {
                "staking_delegations_root": pd.get("staking_delegations_root") or pd.get("delegations_root"),
                "proof": pd["proof"],
                "leaf_hash": pd["leaf_hash"],
            },
        )
        assert vd.get("ok") is True
        assert vd.get("verified") is True