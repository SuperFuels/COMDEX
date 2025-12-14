from __future__ import annotations

import os
import time
from typing import List, Optional


def _pct(xs: List[float], p: float) -> float:
    xs = sorted(xs)
    if not xs:
        return 0.0
    k = int((p / 100.0) * (len(xs) - 1))
    return xs[k]


def _latest_height(c, base: str) -> int:
    r = c.get(f"{base}/api/chain_sim/dev/blocks", params={"limit": 1, "offset": 0})
    r.raise_for_status()
    blocks = r.json().get("blocks") or []
    return int(blocks[0]["height"]) if blocks else 0


def test_glyphchain_perf_smoke():
    import httpx  # dev dep
    import json
    import pathlib
    from datetime import datetime, UTC

    # Prefer GLYPHCHAIN_URL, fall back to CHAIN_SIM_URL for compatibility
    base = os.getenv("GLYPHCHAIN_URL") or os.getenv("CHAIN_SIM_URL") or "http://127.0.0.1:8080"
    N = int(os.getenv("CHAIN_SIM_TXN", "200"))

    genesis = {
        "chain_id": "comdex-dev",
        "network_id": "local",
        "allocs": [
            {"address": "pho1-alice", "balances": {"PHO": "1000000", "TESS": "0"}},
            {"address": "pho1-bob", "balances": {"PHO": "0", "TESS": "0"}},
        ],
        "validators": [],
    }

    timeout = httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=5.0)

    with httpx.Client(timeout=timeout) as c:
        # 1) reset (genesis allocs should be direct-set and fast)
        r = c.post(f"{base}/api/chain_sim/dev/reset", json=genesis, timeout=60.0)
        r.raise_for_status()

        # 2) fetch alice nonce
        a = c.get(f"{base}/api/chain_sim/dev/account", params={"address": "pho1-alice"})
        a.raise_for_status()
        nonce = int(a.json().get("nonce", 0))

        # 3) submit N transfers; measure latency + overall TPS
        lat: List[float] = []
        t_start = time.perf_counter()

        for _ in range(N):
            t0 = time.perf_counter()
            tx = {
                "from_addr": "pho1-alice",
                "nonce": nonce,
                "tx_type": "BANK_SEND",
                "payload": {"denom": "PHO", "to": "pho1-bob", "amount": "1"},
            }
            resp = c.post(f"{base}/api/chain_sim/dev/submit_tx", json=tx)
            resp.raise_for_status()
            j = resp.json()
            # perf test expects applied transfers
            assert j.get("ok") is True
            assert j.get("applied") is True

            nonce += 1
            lat.append((time.perf_counter() - t0) * 1000.0)

        t_end = time.perf_counter()
        elapsed_s = t_end - t_start
        tps = (N / elapsed_s) if elapsed_s > 0 else 0.0

        # 3b) rejected tx should NOT create a block (bad nonce)
        pre_h = _latest_height(c, base)
        bad = c.post(
            f"{base}/api/chain_sim/dev/submit_tx",
            json={
                "from_addr": "pho1-alice",
                "nonce": 999999999,
                "tx_type": "BANK_SEND",
                "payload": {"denom": "PHO", "to": "pho1-bob", "amount": "1"},
            },
        )
        bad.raise_for_status()
        bad_j = bad.json()
        assert bad_j.get("ok") is False
        assert bad_j.get("applied") is False
        post_h = _latest_height(c, base)
        assert post_h == pre_h

        # 4) measure /dev/state
        t0 = time.perf_counter()
        s = c.get(f"{base}/api/chain_sim/dev/state")
        s.raise_for_status()
        state_ms = (time.perf_counter() - t0) * 1000.0
        state_bytes = len(s.content)

        # 5) proof endpoint optional
        proof_ms: Optional[float] = None
        proof_bytes: Optional[int] = None
        proof_implemented = False

        t0 = time.perf_counter()
        p = c.get(f"{base}/api/chain_sim/dev/proof/account", params={"address": "pho1-alice"})
        if p.status_code == 200:
            proof_ms = (time.perf_counter() - t0) * 1000.0
            proof_bytes = len(p.content)
            proof_implemented = True

        print("\n=== glyphchain perf ===")
        print(f"tx_count={N}")
        print(f"elapsed_s={elapsed_s:.4f}")
        print(f"tps_finalized_dev={tps:.2f}")
        print(f"lat_ms_p50={_pct(lat, 50):.2f}  p95={_pct(lat, 95):.2f}  p99={_pct(lat, 99):.2f}")
        print(f"state_ms={state_ms:.2f}  state_bytes={state_bytes}")
        if proof_implemented:
            print(f"proof_ms={proof_ms:.2f}  proof_bytes={proof_bytes}")
        else:
            print("proof: (skipped) /api/chain_sim/dev/proof/account not implemented")

        # write artifact(s)
        out = {
            "ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "glyphchain_url": base,
            "tx_count": N,
            "elapsed_s": elapsed_s,
            "tps": tps,
            "lat_ms": {"p50": _pct(lat, 50), "p95": _pct(lat, 95), "p99": _pct(lat, 99)},
            "state_ms": state_ms,
            "state_bytes": state_bytes,
            "proof_ms": proof_ms,
            "proof_bytes": proof_bytes,
            "proof_implemented": proof_implemented,
        }

        artifacts = pathlib.Path("backend/tests/artifacts")
        artifacts.mkdir(parents=True, exist_ok=True)

        # New preferred name
        (artifacts / "glyphchain_perf_latest.json").write_text(json.dumps(out, indent=2))

        # Back-compat name (remove later once everything switches)
        (artifacts / "chain_sim_perf_latest.json").write_text(json.dumps(out, indent=2))

        # smoke assertions
        assert tps > 0
        assert state_bytes > 0