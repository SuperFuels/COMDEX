from __future__ import annotations

import argparse
import asyncio
import os
import time
from typing import Any, Dict, List, Optional


def _pct(xs: List[float], p: float) -> float:
    xs = sorted(xs)
    if not xs:
        return 0.0
    k = int((p / 100.0) * (len(xs) - 1))
    return xs[k]


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _env_str(name: str, default: str) -> str:
    return os.getenv(name) or default


async def _post(c, base: str, path: str, json: Dict[str, Any], timeout: Optional[float] = None) -> Dict[str, Any]:
    r = await c.post(f"{base}{path}", json=json, timeout=timeout)
    r.raise_for_status()
    return r.json()


async def _get(c, base: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    r = await c.get(f"{base}{path}", params=params)
    r.raise_for_status()
    return r.json()


async def main() -> int:
    import httpx  # dev dep

    ap = argparse.ArgumentParser(description="Concurrent load for chain_sim /dev/submit_tx (safe nonces per sender)")
    ap.add_argument("--base", default=_env_str("CHAIN_SIM_URL", _env_str("GLYPHCHAIN_URL", "http://127.0.0.1:8080")))
    ap.add_argument("--accounts", type=int, default=_env_int("CHAIN_SIM_ACCOUNTS", 50))
    ap.add_argument("--tx-per-account", type=int, default=_env_int("CHAIN_SIM_TX_PER_ACCOUNT", 200))
    ap.add_argument("--max-inflight", type=int, default=_env_int("CHAIN_SIM_MAX_INFLIGHT", 200))
    ap.add_argument("--denom", default=_env_str("CHAIN_SIM_DENOM", "PHO"))
    ap.add_argument("--amount", default=_env_str("CHAIN_SIM_AMOUNT", "1"))
    ap.add_argument("--fund", default=_env_str("CHAIN_SIM_FUND", "100000"))
    ap.add_argument("--sink", default=_env_str("CHAIN_SIM_SINK", "pho1-bob"))
    args = ap.parse_args()

    base: str = args.base.rstrip("/")
    n_accounts: int = max(1, args.accounts)
    tx_per: int = max(1, args.tx_per_account)
    total_txs = n_accounts * tx_per

    # NOTE: BANK_SEND in your engine charges PHO fee per tx.
    # So each sender needs enough PHO to cover (amount + fee) * tx_per.
    # fund default is generous; tune if you want.
    allocs = []
    for i in range(n_accounts):
        allocs.append({"address": f"pho1-s{i}", "balances": {"PHO": str(args.fund), "TESS": "0"}})

    genesis = {
        "chain_id": "comdex-dev",
        "network_id": "local",
        "allocs": allocs + [{"address": args.sink, "balances": {"PHO": "0", "TESS": "0"}}],
        "validators": [{"address": "val1", "self_delegation_tess": "0", "commission": "0"}],
    }

    timeout = httpx.Timeout(connect=5.0, read=60.0, write=60.0, pool=5.0)

    lat_ms: List[float] = []
    ok_applied = 0
    ok_rejected = 0
    http_errors = 0
    other_errors = 0

    sem = asyncio.Semaphore(max(1, args.max_inflight))

    async with httpx.AsyncClient(timeout=timeout) as c:
        # 1) reset
        await _post(c, base, "/api/chain_sim/dev/reset", genesis, timeout=60.0)

        # 2) each sender submits sequential nonces (safe)
        async def run_sender(i: int) -> None:
            nonlocal ok_applied, ok_rejected, http_errors, other_errors
            from_addr = f"pho1-s{i}"
            nonce = 0  # after reset, should be 0; we keep it deterministic

            for _ in range(tx_per):
                async with sem:
                    t0 = time.perf_counter()
                    try:
                        r = await c.post(
                            f"{base}/api/chain_sim/dev/submit_tx",
                            json={
                                "from_addr": from_addr,
                                "nonce": nonce,
                                "tx_type": "BANK_SEND",
                                "payload": {"denom": args.denom, "to": args.sink, "amount": args.amount},
                            },
                        )
                        r.raise_for_status()
                        j = r.json()
                        dt = (time.perf_counter() - t0) * 1000.0
                        lat_ms.append(dt)

                        if j.get("ok") is True and j.get("applied") is True:
                            ok_applied += 1
                            nonce += 1
                        else:
                            # rejected should not advance nonce on-chain, so we DO NOT increment local nonce
                            ok_rejected += 1
                    except httpx.HTTPError:
                        http_errors += 1
                    except Exception:
                        other_errors += 1

        t_start = time.perf_counter()
        await asyncio.gather(*[run_sender(i) for i in range(n_accounts)])
        t_end = time.perf_counter()

        elapsed_s = t_end - t_start
        tps = (ok_applied / elapsed_s) if elapsed_s > 0 else 0.0

        # 3) sanity snapshot (optional, but nice)
        st = await _get(c, base, "/api/chain_sim/dev/state")
        state_root = st.get("state_root")

    print("\n=== concurrent load ===")
    print(f"base={base}")
    print(f"accounts={n_accounts}  tx_per_account={tx_per}  total={total_txs}")
    print(f"elapsed_s={elapsed_s:.4f}")
    print(f"applied={ok_applied}  rejected={ok_rejected}  http_errors={http_errors}  other_errors={other_errors}")
    print(f"tps_applied={tps:.2f}")
    print(f"lat_ms_p50={_pct(lat_ms, 50):.2f}  p95={_pct(lat_ms, 95):.2f}  p99={_pct(lat_ms, 99):.2f}")
    print(f"state_root={state_root}")

    # hard expectations for a dev chain:
    assert http_errors == 0
    assert other_errors == 0
    assert ok_applied > 0
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))