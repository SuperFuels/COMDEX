from __future__ import annotations

import argparse
import asyncio
import os
import time
from collections import Counter
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

    # resiliency knobs
    ap.add_argument("--retries", type=int, default=_env_int("CHAIN_SIM_RETRIES", 10))
    ap.add_argument("--retry-base-ms", type=float, default=float(os.getenv("CHAIN_SIM_RETRY_BASE_MS", "25")))
    ap.add_argument("--reconcile-on-error", action="store_true", default=True)
    ap.add_argument("--no-reconcile-on-error", action="store_true", help="Disable nonce reconciliation on HTTP errors")
    ap.add_argument("--allow-http-errors", type=int, default=_env_int("CHAIN_SIM_ALLOW_HTTP_ERRORS", 0))
    args = ap.parse_args()

    if args.no_reconcile_on_error:
        args.reconcile_on_error = False

    base: str = args.base.rstrip("/")
    n_accounts: int = max(1, args.accounts)
    tx_per: int = max(1, args.tx_per_account)
    total_txs = n_accounts * tx_per

    allocs = [{"address": f"pho1-s{i}", "balances": {"PHO": str(args.fund), "TESS": "0"}} for i in range(n_accounts)]

    genesis = {
        "chain_id": "comdex-dev",
        "network_id": "local",
        "allocs": allocs + [{"address": args.sink, "balances": {"PHO": "0", "TESS": "0"}}],
        "validators": [{"address": "val1", "self_delegation_tess": "0", "commission": "0"}],
    }

    # More forgiving timeouts for high concurrency (pool timeout is often the first to bite).
    timeout = httpx.Timeout(connect=10.0, read=120.0, write=120.0, pool=120.0)

    # Ensure client-side connection pool doesn't silently cap inflight.
    limits = httpx.Limits(
        max_connections=max(200, args.max_inflight * 2),
        max_keepalive_connections=max(200, args.max_inflight * 2),
    )

    sem = asyncio.Semaphore(max(1, args.max_inflight))

    lat_ms: List[float] = []
    ok_applied = 0
    ok_rejected = 0
    http_errors = 0
    other_errors = 0
    lost_responses_reconciled = 0

    http_error_kinds = Counter()
    http_statuses = Counter()

    # protect shared counters/list (still single-threaded, but this avoids weirdness while awaited)
    lock = asyncio.Lock()

    async with httpx.AsyncClient(timeout=timeout, limits=limits) as c:
        # 1) reset
        await _post(c, base, "/api/chain_sim/dev/reset", genesis, timeout=60.0)

        async def get_remote_nonce(addr: str) -> int:
            j = await _get(c, base, "/api/chain_sim/dev/account", params={"address": addr})
            try:
                return int(j.get("nonce", 0))
            except Exception:
                return 0

        async def run_sender(i: int) -> None:
            nonlocal ok_applied, ok_rejected, http_errors, other_errors, lost_responses_reconciled

            from_addr = f"pho1-s{i}"
            nonce = 0  # expected after reset
            local_lat: List[float] = []

            while nonce < tx_per:
                async with sem:
                    t0 = time.perf_counter()
                    attempt = 0

                    while True:
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

                            local_lat.append((time.perf_counter() - t0) * 1000.0)

                            if j.get("ok") is True and j.get("applied") is True:
                                async with lock:
                                    ok_applied += 1
                                nonce += 1
                                break

                            # If rejected, do NOT increment nonce.
                            async with lock:
                                ok_rejected += 1
                            # In this dev load test, rejections are unexpected; stop this sender.
                            return

                        except httpx.HTTPStatusError as e:
                            async with lock:
                                http_errors += 1
                                http_error_kinds[f"HTTPStatusError:{e.response.status_code}"] += 1
                                try:
                                    http_statuses[int(e.response.status_code)] += 1
                                except Exception:
                                    pass

                        except httpx.PoolTimeout as e:
                            async with lock:
                                http_errors += 1
                                http_error_kinds[type(e).__name__] += 1

                        except httpx.TimeoutException as e:
                            async with lock:
                                http_errors += 1
                                http_error_kinds[type(e).__name__] += 1

                        except httpx.ConnectError as e:
                            async with lock:
                                http_errors += 1
                                http_error_kinds[type(e).__name__] += 1

                        except httpx.TransportError as e:
                            async with lock:
                                http_errors += 1
                                http_error_kinds[type(e).__name__] += 1

                        except httpx.HTTPError as e:
                            async with lock:
                                http_errors += 1
                                http_error_kinds[type(e).__name__] += 1

                        except Exception:
                            async with lock:
                                other_errors += 1
                            return

                        # If we got here, the request failed and we don't know if the tx applied.
                        # Reconcile by checking on-chain nonce. If it advanced, count it and move on.
                        if args.reconcile_on_error:
                            try:
                                remote = await get_remote_nonce(from_addr)
                                if remote > nonce:
                                    delta = remote - nonce
                                    async with lock:
                                        ok_applied += delta
                                        lost_responses_reconciled += delta
                                    nonce = remote
                                    break
                            except Exception:
                                pass

                        attempt += 1
                        if attempt > max(0, args.retries):
                            return

                        # small exponential backoff
                        backoff_ms = args.retry_base_ms * (2 ** min(6, attempt))
                        await asyncio.sleep(backoff_ms / 1000.0)

            async with lock:
                lat_ms.extend(local_lat)

        t_start = time.perf_counter()
        await asyncio.gather(*[run_sender(i) for i in range(n_accounts)])
        t_end = time.perf_counter()

        elapsed_s = t_end - t_start
        tps = (ok_applied / elapsed_s) if elapsed_s > 0 else 0.0

        st = await _get(c, base, "/api/chain_sim/dev/state")
        state_root = st.get("state_root")

    print("\n=== concurrent load ===")
    print(f"base={base}")
    print(f"accounts={n_accounts}  tx_per_account={tx_per}  total={total_txs}")
    print(f"max_inflight={args.max_inflight}  retries={args.retries}  reconcile_on_error={args.reconcile_on_error}")
    print(f"elapsed_s={elapsed_s:.4f}")
    print(
        f"applied={ok_applied}  rejected={ok_rejected}  http_errors={http_errors}  other_errors={other_errors}  "
        f"reconciled_applied={lost_responses_reconciled}"
    )
    print(f"tps_applied={tps:.2f}")
    print(f"lat_ms_p50={_pct(lat_ms, 50):.2f}  p95={_pct(lat_ms, 95):.2f}  p99={_pct(lat_ms, 99):.2f}")
    print(f"state_root={state_root}")

    if http_errors:
        print(f"http_error_kinds={dict(http_error_kinds)}")
        if http_statuses:
            print(f"http_statuses={dict(http_statuses)}")

    # expectations:
    assert other_errors == 0
    assert ok_rejected == 0
    assert ok_applied == total_txs, f"expected applied={total_txs}, got {ok_applied}"
    assert http_errors <= int(args.allow_http_errors), (
        f"http_errors={http_errors} > allow_http_errors={args.allow_http_errors}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))