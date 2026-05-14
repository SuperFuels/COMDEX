from __future__ import annotations

import os
import time
import httpx

BASE = os.getenv("GLYPHCHAIN_URL") or os.getenv("CHAIN_SIM_URL") or "http://127.0.0.1:8080"
TIMEOUT = httpx.Timeout(connect=5.0, read=60.0, write=60.0, pool=10.0)

def test_state_scale_accounts():
    n = int(os.getenv("CHAIN_SIM_ACCTS", "1000"))

    # generate N funded accounts at genesis (fast path if apply_genesis_allocs exists)
    allocs = [{"address": f"pho1-a{i}", "balances": {"PHO": "10", "TESS": "10"}} for i in range(n)]
    genesis = {
        "chain_id": "comdex-dev",
        "network_id": "local",
        "allocs": allocs,
        "validators": [{"address": "val1", "self_delegation_tess": "0", "commission": "0"}],
    }

    with httpx.Client(timeout=TIMEOUT) as c:
        r = c.post(f"{BASE}/api/chain_sim/dev/reset", json=genesis)
        r.raise_for_status()

        # /dev/state timing
        t0 = time.perf_counter()
        s = c.get(f"{BASE}/api/chain_sim/dev/state")
        s.raise_for_status()
        state_ms = (time.perf_counter() - t0) * 1000.0

        st = s.json().get("state") or {}
        bank_root = ((st.get("bank") or {}) if isinstance(st, dict) else {}).get("root")
        assert isinstance(bank_root, str) and len(bank_root) == 64

        # proof timing (pick a middle account)
        addr = f"pho1-a{n//2}"
        t0 = time.perf_counter()
        p = c.get(f"{BASE}/api/chain_sim/dev/proof/account", params={"address": addr})
        p.raise_for_status()
        proof_ms = (time.perf_counter() - t0) * 1000.0

        pj = p.json()
        assert pj.get("bank_accounts_root") == bank_root

        print(f"\n=== state scale === n_accts={n} state_ms={state_ms:.2f} acct_proof_ms={proof_ms:.2f}")