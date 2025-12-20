# backend/tests/glyphchain/test_consensus_pr6_competing_proposal_same_hr_gate.py
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Tuple

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.glyphchain]

from backend.tests.helpers import start_n_nodes, stop_nodes, http_get, http_post
from backend.modules.p2p.crypto_ed25519 import canonical_p2p_sign_bytes, sign_ed25519


def _now_ms() -> float:
    return float(time.time() * 1000.0)


def _mk_env(*, src, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "PROPOSAL",
        "from_node_id": src.node_id,
        "from_val_id": src.val_id,
        "chain_id": src.chain_id,
        "ts_ms": _now_ms(),
        "payload": payload,
        "hops": 0,
    }


async def _wait_ok(base_url: str, path: str, *, timeout_s: float = 240.0) -> Dict[str, Any]:
    deadline = time.time() + timeout_s
    last: Any = None
    while time.time() < deadline:
        try:
            r = await http_get(base_url, path, timeout_s=6.0)
            if int(r.get("status") or 0) == 200:
                j = r.get("json") or {}
                if isinstance(j, dict) and j.get("ok") is True:
                    return j
                last = {"status": r.get("status"), "json": j}
            else:
                last = r
        except Exception as e:
            last = repr(e)
        await asyncio.sleep(0.25)
    raise RuntimeError(f"endpoint not ready: {base_url}{path} last={last!r}")


async def _wait_dst_leader_slot(
    dst_base: str,
    *,
    want_leader: str,
    timeout_s: float = 30.0,
) -> Tuple[int, int, Dict[str, Any]]:
    """
    Wait until dst reports leader==want_leader for its CURRENT (height, round).
    We then inject proposals for exactly that (h,r) so the handler actually tracks/stores them.
    """
    deadline = time.time() + timeout_s
    last: Any = None
    while time.time() < deadline:
        st = await http_get(dst_base, "/api/p2p/consensus_status", timeout_s=10.0)
        if int(st.get("status") or 0) != 200:
            last = st
            await asyncio.sleep(0.25)
            continue

        j = st.get("json") or {}
        if not isinstance(j, dict):
            last = j
            await asyncio.sleep(0.25)
            continue

        h = int(j.get("height") or 0)
        r = int(j.get("round") or 0)
        leader = str(j.get("leader") or "")

        if h > 0 and leader == want_leader:
            return h, r, j

        last = {"h": h, "r": r, "leader": leader, "want": want_leader, "have_proposal": j.get("have_proposal")}
        await asyncio.sleep(0.25)

    raise RuntimeError(f"dst never entered leader slot for {want_leader}; last={last!r}")


def _sign_proposal(*, chain_id: str, priv_hex: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a shallow copy with sig_hex attached.
    Sign bytes must NOT include sig_hex itself.
    """
    unsigned = {k: payload[k] for k in payload.keys() if k != "sig_hex"}
    sig_msg = canonical_p2p_sign_bytes(msg_type="PROPOSAL", chain_id=chain_id, payload=unsigned)
    out = dict(payload)
    out["sig_hex"] = sign_ed25519(priv_hex, sig_msg)
    return out


@pytest.mark.asyncio
async def test_consensus_pr6_competing_proposal_same_hr_gate() -> None:
    nodes = await start_n_nodes(3, base_port=18080, chain_id="glyphchain-dev")
    try:
        # wait until nodes are actually serving requests
        for n in nodes:
            await _wait_ok(n.base_url, "/api/p2p/peers", timeout_s=240.0)
            await _wait_ok(n.base_url, "/api/p2p/consensus_status", timeout_s=240.0)

        src = nodes[0]  # proposer/signer (val1)
        dst = nodes[1]  # receiver

        # ensure src is in validator set
        st0 = await http_get(dst.base_url, "/api/p2p/consensus_status", timeout_s=10.0)
        assert int(st0.get("status") or 0) == 200, f"status fetch failed: {st0}"
        j0 = st0.get("json") or {}
        ids = j0.get("validators") or []
        assert isinstance(ids, list) and src.val_id in ids, f"missing validators/src in status: {j0}"

        # pick dst’s CURRENT (h,r) where leader==src so proposal will be tracked
        h, r, _jslot = await _wait_dst_leader_slot(dst.base_url, want_leader=src.val_id, timeout_s=45.0)

        # Canonical block_id format used by engine tick + _canon_block_id()
        canonical_bid = f"h{h}-r{r}-P{src.val_id}"

        # --- 1) Send canonical proposal => accept OR treat as dup (200)
        payload1 = {
            "height": int(h),
            "round": int(r),
            "proposer": src.val_id,
            "block_id": canonical_bid,
            "block": {},
            "ts_ms": _now_ms(),
        }
        payload1 = _sign_proposal(chain_id=src.chain_id, priv_hex=src.p2p_privkey_hex, payload=payload1)

        r1 = await http_post(dst.base_url, "/api/p2p/proposal", _mk_env(src=src, payload=payload1), timeout_s=12.0)
        assert int(r1.get("status") or 0) == 200, f"expected 200 for canonical/dup proposal, got: {r1}"
        j1 = r1.get("json") or {}
        assert isinstance(j1, dict) and j1.get("ok") is True, f"expected ok:true, got: {r1}"

        # best-effort: dst should now (or already) have canonical proposal recorded
        # (don’t assert height/round movement — engine may advance independently)
        st1 = await http_get(dst.base_url, "/api/p2p/consensus_status", timeout_s=10.0)
        assert int(st1.get("status") or 0) == 200
        js1 = st1.get("json") or {}
        if isinstance(js1, dict) and int(js1.get("height") or 0) == int(h) and int(js1.get("round") or 0) == int(r):
            # if still on the slot, proposal_block_id must be canonical
            if js1.get("proposal_block_id") is not None:
                assert js1.get("proposal_block_id") == canonical_bid, f"dst stored wrong proposal_block_id: {js1}"

        # --- 2) Send competing proposal same (h,r) but different block_id => must reject
        bad_bid = canonical_bid + "-conflict"
        payload2 = {
            "height": int(h),
            "round": int(r),
            "proposer": src.val_id,
            "block_id": bad_bid,
            "block": {},
            "ts_ms": _now_ms(),
        }
        payload2 = _sign_proposal(chain_id=src.chain_id, priv_hex=src.p2p_privkey_hex, payload=payload2)

        r2 = await http_post(dst.base_url, "/api/p2p/proposal", _mk_env(src=src, payload=payload2), timeout_s=12.0)
        assert int(r2.get("status") or 0) == 400, f"expected 400 for competing proposal, got: {r2}"

        # --- 3) Replay identical canonical proposal => should be accepted (dup) (200)
        # keep exact same fields to match any fingerprinting logic
        payload3 = dict(payload1)
        r3 = await http_post(dst.base_url, "/api/p2p/proposal", _mk_env(src=src, payload=payload3), timeout_s=12.0)
        assert int(r3.get("status") or 0) == 200, f"expected 200 for duplicate identical proposal, got: {r3}"
        j3 = r3.get("json") or {}
        assert isinstance(j3, dict) and j3.get("ok") is True, f"expected ok:true on duplicate, got: {r3}"

    finally:
        await stop_nodes(nodes)