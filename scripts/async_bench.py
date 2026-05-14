import argparse, asyncio, time
import httpx

BASE_DEFAULT="http://127.0.0.1:8080"

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE_DEFAULT)
    ap.add_argument("--accounts", type=int, default=5000)
    ap.add_argument("--tx-per-account", type=int, default=2)
    ap.add_argument("--max-inflight", type=int, default=50)
    args = ap.parse_args()

    base = args.base.rstrip("/")
    accounts = args.accounts
    tx_per = args.tx_per_account
    max_inflight = args.max_inflight
    total = accounts * tx_per

    sem = asyncio.Semaphore(max_inflight)

    async with httpx.AsyncClient(timeout=180.0) as c:
        # reset
        genesis={
            "chain_id":"comdex-dev","network_id":"local",
            "allocs":[{"address":f"pho1-s{i}","balances":{"PHO":"100000","TESS":"0"}} for i in range(accounts)]
                    + [{"address":"pho1-bob","balances":{"PHO":"0","TESS":"0"}}],
            "validators":[{"address":"val1","self_delegation_tess":"0","commission":"0"}]
        }
        r = await c.post(f"{base}/api/chain_sim/dev/reset", json=genesis)
        r.raise_for_status()

        async def submit(i: int, n: int):
            async with sem:
                rr = await c.post(f"{base}/api/chain_sim/dev/submit_tx_async", json={
                    "from_addr": f"pho1-s{i}",
                    "nonce": n,
                    "tx_type": "BANK_SEND",
                    "payload": {"denom":"PHO","to":"pho1-bob","amount":"1"},
                })
                rr.raise_for_status()

        t0 = time.perf_counter()
        await asyncio.gather(*[
            submit(i, n)
            for i in range(accounts)
            for n in range(tx_per)
        ])
        t1 = time.perf_counter()

        ingest_s = t1 - t0
        ingest_tps = total / ingest_s if ingest_s > 0 else 0.0

        # wait for finality
        while True:
            m = (await c.get(f"{base}/api/chain_sim/dev/queue_metrics")).json()
            applied = int(m["metrics"]["applied_total"])
            if applied >= total:
                break
            await asyncio.sleep(0.05)

        t2 = time.perf_counter()
        final_s = t2 - t0
        final_tps = total / final_s if final_s > 0 else 0.0

        print("ingest:", {"elapsed_s": round(ingest_s,4), "tps": round(ingest_tps,2)})
        print("finality:", {"elapsed_s": round(final_s,4), "tps": round(final_tps,2)})
        print("queue_metrics:", m["metrics"])
        print("finality_ms:", m.get("finality_ms"))

if __name__ == "__main__":
    asyncio.run(main())
