from __future__ import annotations

import argparse
import json
import time
import urllib.request
from typing import Any, Dict, List, Tuple


def http_json(method: str, url: str, body: Dict[str, Any] | None = None) -> Dict[str, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def pct(xs: List[float], p: float) -> float:
    if not xs:
        return 0.0
    xs2 = sorted(xs)
    k = int((p / 100.0) * (len(xs2) - 1))
    return float(xs2[k])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8080")
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--inflight", type=int, default=100)
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--out", default="backend/tests/artifacts/glyphchain_perf_latest.json")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    reset_url = f"{base}/api/chain_sim/dev/reset"
    submit_url = f"{base}/api/chain_sim/dev/submit_tx_async"
    status_url = f"{base}/api/chain_sim/dev/tx_status"

    # reset
    r = http_json("POST", reset_url, {
        "chain_id": "glyphchain-dev",
        "network_id": "devnet",
        "allocs": [{"address": "pho1-alice", "balances": {"PHO": str(args.n + 10000)}}],
        "validators": [],
    })

    sig_mode = ((r.get("config") or {}).get("CHAIN_SIM_SIG_MODE") or "off")
    if sig_mode != "off":
        print(f"[warn] CHAIN_SIM_SIG_MODE={sig_mode} (perf sweep assumes off unless you sign requests)")

    t0 = time.time()
    next_nonce = 1

    inflight: List[Tuple[str, float]] = []  # (qid, accepted_ms)
    finality_ms: List[float] = []
    counts = {"finalized": 0, "rejected": 0, "error": 0}

    def poll_once() -> None:
        nonlocal inflight
        keep: List[Tuple[str, float]] = []
        for qid, acc_ms in inflight:
            try:
                st = http_json("GET", f"{status_url}/{qid}")
                s = (st.get("status") or {}).get("state")
                if s in ("finalized", "rejected", "error"):
                    counts[s] += 1
                    done = float((st.get("status") or {}).get("done_at_ms") or 0.0)
                    if s == "finalized" and done > 0:
                        finality_ms.append(done - acc_ms)
                else:
                    keep.append((qid, acc_ms))
            except Exception:
                keep.append((qid, acc_ms))
        inflight = keep

    # main loop
    while next_nonce <= args.n:
        while len(inflight) < max(1, args.inflight) and next_nonce <= args.n:
            body = {
                "from_addr": "pho1-alice",
                "nonce": next_nonce,
                "tx_type": "BANK_BURN",
                "payload": {"denom": "PHO", "amount": 1},
            }
            resp = http_json("POST", submit_url, body)
            qid = str(resp.get("qid") or "")
            if not qid:
                raise SystemExit(f"submit failed: {resp}")
            inflight.append((qid, time.time() * 1000.0))
            next_nonce += 1

        poll_once()
        time.sleep(0.005)

    # drain
    deadline = time.time() + max(1.0, float(args.timeout))
    while inflight and time.time() < deadline:
        poll_once()
        time.sleep(0.01)

    elapsed_s = max(1e-6, time.time() - t0)
    out = {
        "ok": True,
        "base": base,
        "n": args.n,
        "inflight": args.inflight,
        "elapsed_s": elapsed_s,
        "ingest_tps": float(args.n) / elapsed_s,
        "counts": counts,
        "finality_ms": {
            "count": len(finality_ms),
            "p50": pct(finality_ms, 50),
            "p95": pct(finality_ms, 95),
            "p99": pct(finality_ms, 99),
        },
        "timestamp_ms": int(time.time() * 1000),
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)

    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())