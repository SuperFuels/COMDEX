from __future__ import annotations

import os
import time
from typing import List, Optional, Any, Dict


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

    base = os.getenv("GLYPHCHAIN_URL") or os.getenv("CHAIN_SIM_URL") or "http://127.0.0.1:8080"
    N = int(os.getenv("CHAIN_SIM_TXN", "200"))

    # include a validator so staking proof endpoints (if present) have something to prove
    genesis = {
        "chain_id": "comdex-dev",
        "network_id": "local",
        "allocs": [
            {"address": "pho1-alice", "balances": {"PHO": "1000000", "TESS": "1000000"}},
            {"address": "pho1-bob", "balances": {"PHO": "0", "TESS": "0"}},
        ],
        "validators": [
            {"address": "val1", "self_delegation_tess": "0", "commission": "0"},
        ],
    }

    timeout = httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=5.0)

    with httpx.Client(timeout=timeout) as c:
        # 1) reset (genesis allocs should be direct-set and fast)
        r = c.post(f"{base}/api/chain_sim/dev/reset", json=genesis, timeout=60.0)
        r.raise_for_status()

        # (optional) create a delegation so delegation proofs (if present) have a leaf
        # If STAKING_DELEGATE isn't wired, we just skip this.
        try:
            a = c.get(f"{base}/api/chain_sim/dev/account", params={"address": "pho1-alice"})
            a.raise_for_status()
            st_nonce = int(a.json().get("nonce", 0))
            tx = {
                "from_addr": "pho1-alice",
                "nonce": st_nonce,
                "tx_type": "STAKING_DELEGATE",
                "payload": {"validator": "val1", "amount_tess": "5"},
            }
            resp = c.post(f"{base}/api/chain_sim/dev/submit_tx", json=tx)
            if resp.status_code == 200:
                j = resp.json()
                # only enforce if it's wired and applied
                if j.get("ok") is True and j.get("applied") is True:
                    pass
        except Exception:
            pass

        # 2) fetch alice nonce (for transfers)
        a = c.get(f"{base}/api/chain_sim/dev/account", params={"address": "pho1-alice"})
        a.raise_for_status()
        nonce = int(a.json().get("nonce", 0))

        # track last applied tx for tx-proof timing
        last_tx_id: Optional[str] = None
        last_tx_hash: Optional[str] = None
        last_block_height: Optional[int] = None

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

            assert j.get("ok") is True
            assert j.get("applied") is True

            # record last applied tx identity (for proof timing)
            last_tx_id = j.get("tx_id")
            last_tx_hash = j.get("tx_hash")
            last_block_height = j.get("block_height")

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
        assert bad_j.get("ok") is True
        assert bad_j.get("applied") is False
        assert "tx_id" not in bad_j

        post_h = _latest_height(c, base)
        assert post_h == pre_h

        # 4) measure /dev/state
        t0 = time.perf_counter()
        s = c.get(f"{base}/api/chain_sim/dev/state")
        s.raise_for_status()
        state_ms = (time.perf_counter() - t0) * 1000.0
        state_bytes = len(s.content)

        state_j: Dict[str, Any] = s.json()

        committed_bank_root: Optional[str] = None
        committed_validators_root: Optional[str] = None
        committed_delegations_root: Optional[str] = None

        try:
            st = state_j.get("state") or {}
            bank_view = st.get("bank") if isinstance(st, dict) else None
            if isinstance(bank_view, dict):
                v = bank_view.get("root")
                if isinstance(v, str) and len(v) == 64:
                    committed_bank_root = v

            st_view = st.get("staking") if isinstance(st, dict) else None
            if isinstance(st_view, dict):
                vr = st_view.get("validators_root")
                dr = st_view.get("delegations_root")
                if isinstance(vr, str) and len(vr) == 64:
                    committed_validators_root = vr
                if isinstance(dr, str) and len(dr) == 64:
                    committed_delegations_root = dr
        except Exception:
            pass

        # 5) account proof timing (optional, but preferred)
        acct_proof_ms: Optional[float] = None
        acct_proof_bytes: Optional[int] = None
        acct_proof_root_matches_state: Optional[bool] = None
        acct_proof_implemented = False

        t0 = time.perf_counter()
        p = c.get(f"{base}/api/chain_sim/dev/proof/account", params={"address": "pho1-alice"})
        if p.status_code == 200:
            acct_proof_ms = (time.perf_counter() - t0) * 1000.0
            acct_proof_bytes = len(p.content)
            acct_proof_implemented = True
            try:
                pj = p.json()
                proof_root = pj.get("bank_accounts_root")
                if isinstance(proof_root, str) and isinstance(committed_bank_root, str):
                    acct_proof_root_matches_state = (proof_root == committed_bank_root)
            except Exception:
                acct_proof_root_matches_state = None

        # 6) tx proof timing + REQUIRED verify (when proof endpoint exists)
        tx_proof_ms: Optional[float] = None
        tx_proof_bytes: Optional[int] = None
        tx_proof_verified: Optional[bool] = None
        tx_proof_implemented = False

        if last_tx_id:
            t0 = time.perf_counter()
            pt = c.get(f"{base}/api/chain_sim/dev/proof/tx", params={"tx_id": last_tx_id})
            if pt.status_code == 200:
                tx_proof_ms = (time.perf_counter() - t0) * 1000.0
                tx_proof_bytes = len(pt.content)
                tx_proof_implemented = True

                ptj = pt.json()
                vt = c.post(
                    f"{base}/api/chain_sim/dev/proof/verify_tx",
                    json={
                        "tx_hash": ptj.get("tx_hash") or last_tx_hash,
                        "txs_root": ptj.get("txs_root"),
                        "proof": ptj.get("proof") or [],
                    },
                )
                vt.raise_for_status()
                tx_proof_verified = bool(vt.json().get("verified"))

                # verify endpoint exists -> enforce correctness
                assert tx_proof_verified is True

        # 7) staking proof timings (optional; skip cleanly if not implemented)
        staking_validator_proof_ms: Optional[float] = None
        staking_validator_proof_bytes: Optional[int] = None
        staking_validator_root_matches_state: Optional[bool] = None
        staking_validator_proof_implemented = False

        t0 = time.perf_counter()
        pv = c.get(f"{base}/api/staking/dev/proof/validator", params={"address": "val1"})
        if pv.status_code == 200:
            staking_validator_proof_ms = (time.perf_counter() - t0) * 1000.0
            staking_validator_proof_bytes = len(pv.content)
            staking_validator_proof_implemented = True
            try:
                pvj = pv.json()
                vroot = pvj.get("validators_root") or pvj.get("staking_validators_root")
                if isinstance(vroot, str) and isinstance(committed_validators_root, str):
                    staking_validator_root_matches_state = (vroot == committed_validators_root)
            except Exception:
                staking_validator_root_matches_state = None

        staking_delegation_proof_ms: Optional[float] = None
        staking_delegation_proof_bytes: Optional[int] = None
        staking_delegation_root_matches_state: Optional[bool] = None
        staking_delegation_proof_implemented = False

        t0 = time.perf_counter()
        pd = c.get(
            f"{base}/api/staking/dev/proof/delegation",
            params={"delegator": "pho1-alice", "validator": "val1"},
        )

        if pd.status_code == 200:
            staking_delegation_proof_ms = (time.perf_counter() - t0) * 1000.0
            staking_delegation_proof_bytes = len(pd.content)
            staking_delegation_proof_implemented = True
            try:
                pdj = pd.json()
                droot = pdj.get("delegations_root") or pdj.get("staking_delegations_root")
                if isinstance(droot, str) and isinstance(committed_delegations_root, str):
                    staking_delegation_root_matches_state = (droot == committed_delegations_root)
            except Exception:
                staking_delegation_root_matches_state = None
        else:
            # distinguish "route not mounted" vs "no delegation leaf"
            try:
                dj = pd.json()
                detail = dj.get("detail")
                if detail == "delegation not found":
                    staking_delegation_proof_implemented = True   # endpoint exists, but no leaf yet
                elif detail == "Not Found":
                    staking_delegation_proof_implemented = False  # route missing
            except Exception:
                pass

        print("\n=== glyphchain perf ===")
        print(f"tx_count={N}")
        print(f"elapsed_s={elapsed_s:.4f}")
        print(f"tps_finalized_dev={tps:.2f}")
        print(f"lat_ms_p50={_pct(lat, 50):.2f}  p95={_pct(lat, 95):.2f}  p99={_pct(lat, 99):.2f}")
        print(f"state_ms={state_ms:.2f}  state_bytes={state_bytes}")

        if acct_proof_implemented:
            print(f"acct_proof_ms={acct_proof_ms:.2f}  acct_proof_bytes={acct_proof_bytes}")
            print(f"acct_proof_root_matches_state={acct_proof_root_matches_state}")
        else:
            print("acct proof: (skipped) /api/chain_sim/dev/proof/account not implemented")

        if tx_proof_implemented:
            print(f"tx_proof_ms={tx_proof_ms:.2f}  tx_proof_bytes={tx_proof_bytes}  verified={tx_proof_verified}")
        else:
            print("tx proof: (skipped) /api/chain_sim/dev/proof/tx not implemented")

        if staking_validator_proof_implemented:
            print(
                f"staking_validator_proof_ms={staking_validator_proof_ms:.2f}  "
                f"staking_validator_proof_bytes={staking_validator_proof_bytes}"
            )
            print(f"staking_validator_root_matches_state={staking_validator_root_matches_state}")
        else:
            print("staking validator proof: (skipped) /api/staking/dev/proof/validator not implemented")

        if staking_delegation_proof_implemented:
            print(
                f"staking_delegation_proof_ms={staking_delegation_proof_ms:.2f}  "
                f"staking_delegation_proof_bytes={staking_delegation_proof_bytes}"
            )
            print(f"staking_delegation_root_matches_state={staking_delegation_root_matches_state}")
        else:
            print("staking delegation proof: (skipped) /api/staking/dev/proof/delegation not implemented")

        out: Dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "glyphchain_url": base,
            "tx_count": N,
            "elapsed_s": elapsed_s,
            "tps": tps,
            "lat_ms": {"p50": _pct(lat, 50), "p95": _pct(lat, 95), "p99": _pct(lat, 99)},
            "state_ms": state_ms,
            "state_bytes": state_bytes,
            # account proof
            "acct_proof_ms": acct_proof_ms,
            "acct_proof_bytes": acct_proof_bytes,
            "acct_proof_implemented": acct_proof_implemented,
            "acct_proof_root_matches_state": acct_proof_root_matches_state,
            # tx proof
            "tx_proof_ms": tx_proof_ms,
            "tx_proof_bytes": tx_proof_bytes,
            "tx_proof_implemented": tx_proof_implemented,
            "tx_proof_verified": tx_proof_verified,
            # staking proofs
            "staking_validator_proof_ms": staking_validator_proof_ms,
            "staking_validator_proof_bytes": staking_validator_proof_bytes,
            "staking_validator_proof_implemented": staking_validator_proof_implemented,
            "staking_validator_root_matches_state": staking_validator_root_matches_state,
            "staking_delegation_proof_ms": staking_delegation_proof_ms,
            "staking_delegation_proof_bytes": staking_delegation_proof_bytes,
            "staking_delegation_proof_implemented": staking_delegation_proof_implemented,
            "staking_delegation_root_matches_state": staking_delegation_root_matches_state,
            # last tx metadata
            "last_tx_id": last_tx_id,
            "last_tx_hash": last_tx_hash,
            "last_block_height": last_block_height,
        }

        artifacts = pathlib.Path("backend/tests/artifacts")
        artifacts.mkdir(parents=True, exist_ok=True)
        (artifacts / "glyphchain_perf_latest.json").write_text(json.dumps(out, indent=2))
        (artifacts / "chain_sim_perf_latest.json").write_text(json.dumps(out, indent=2))

        assert tps > 0
        assert state_bytes > 0