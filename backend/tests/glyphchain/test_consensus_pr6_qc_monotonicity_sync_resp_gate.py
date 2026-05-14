from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional, Tuple

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.glyphchain]

from backend.tests.helpers import start_n_nodes, stop_nodes, http_get, http_post


def _now_ms() -> float:
    return float(time.time() * 1000.0)


def _qc_key(qc: Any) -> Tuple[int, int]:
    """
    qc can be dict or None.
    ordering key: (height, round)
    """
    if not isinstance(qc, dict):
        return (0, 0)
    try:
        h = int(qc.get("height") or 0)
    except Exception:
        h = 0
    try:
        r = int(qc.get("round") or 0)
    except Exception:
        r = 0
    return (h, r)


async def _get_status(node) -> Dict[str, Any]:
    r = await http_get(node.base_url, "/api/p2p/consensus_status", timeout_s=10.0)
    assert int(r.get("status") or 0) == 200, r
    j = r.get("json") or {}
    assert isinstance(j, dict)
    return j


async def _wait_for_fh_at_least(node, want: int, *, timeout_s: float = 40.0) -> Dict[str, Any]:
    deadline = time.time() + timeout_s
    seen: Dict[int, Dict[str, Any]] = {}
    while time.time() < deadline:
        st = await _get_status(node)
        fh = int(st.get("finalized_height") or 0)
        if isinstance(st.get("last_qc"), dict):
            seen[fh] = st
        if fh >= want:
            return st
        await asyncio.sleep(0.25)
    raise AssertionError(f"timeout waiting for finalized_height >= {want}")


@pytest.mark.asyncio
async def test_consensus_pr6_qc_monotonicity_sync_resp_gate() -> None:
    nodes = await start_n_nodes(3, base_port=18410, chain_id="glyphchain-dev")
    try:
        target = nodes[0]
        sender = nodes[1]

        # Wait until we have some non-trivial finalized state.
        st_tip = await _wait_for_fh_at_least(target, 2, timeout_s=60.0)
        tip_fh = int(st_tip.get("finalized_height") or 0)
        tip_qc = st_tip.get("last_qc")
        assert isinstance(tip_qc, dict) and int(tip_qc.get("height") or 0) == tip_fh, st_tip

        # Find an older (fh-1) QC by waiting for fh to pass it (best-effort).
        # If we can't, we still test "ignore behind" with a structurally plausible payload by reusing tip_qc
        # but lowering both finalized_height and qc.height (will likely 400, which is allowed).
        old_fh = max(1, tip_fh - 1)

        # Try to capture a real qc for old_fh by polling history quickly.
        qc_old: Optional[Dict[str, Any]] = None
        # poll other nodes too; they may have the older qc cached in status while catching up
        for _ in range(20):
            for n in nodes:
                stn = await _get_status(n)
                fh_n = int(stn.get("finalized_height") or 0)
                qc_n = stn.get("last_qc")
                if fh_n == old_fh and isinstance(qc_n, dict) and int(qc_n.get("height") or 0) == old_fh:
                    qc_old = qc_n
                    break
            if qc_old is not None:
                break
            await asyncio.sleep(0.15)

        if qc_old is None:
            qc_old = dict(tip_qc)
            qc_old["height"] = int(old_fh)

        env = {
            "type": "SYNC_RESP",
            "from_node_id": sender.node_id,
            "from_val_id": sender.val_id,
            "chain_id": sender.chain_id,
            "ts_ms": _now_ms(),
            "payload": {
                "finalized_height": int(old_fh),
                "last_qc": qc_old,
                "round": 0,
            },
            "hops": 0,
        }

        rr = await http_post(target.base_url, "/api/p2p/sync_resp", env, timeout_s=10.0)
        stc = int(rr.get("status") or 0)
        assert stc in (200, 400, 403), rr  # never 500

        st_after = await _get_status(target)
        after_fh = int(st_after.get("finalized_height") or 0)
        after_qc = st_after.get("last_qc")

        # finalized_height must not decrease
        assert after_fh >= tip_fh, (st_tip, st_after)

        # last_qc must not regress (by (height, round))
        assert _qc_key(after_qc) >= _qc_key(tip_qc), (st_tip, st_after)

    finally:
        await stop_nodes(nodes)