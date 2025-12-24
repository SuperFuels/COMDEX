from __future__ import annotations

import time
from typing import Any, Dict

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.glyphchain]

from backend.tests.helpers import start_n_nodes, stop_nodes, http_get, http_post


def _now_ms() -> float:
    return float(time.time() * 1000.0)


def _mk_env(*, src, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "SYNC_RESP",
        "from_node_id": src.node_id,
        "from_val_id": src.val_id,
        "chain_id": src.chain_id,
        "ts_ms": _now_ms(),
        "payload": payload,
        "hops": 0,
    }


async def _get_status(node) -> Dict[str, Any]:
    r = await http_get(node.base_url, "/api/p2p/consensus_status", timeout_s=10.0)
    assert int(r.get("status") or 0) == 200, r
    j = r.get("json") or {}
    assert isinstance(j, dict)
    return j


@pytest.mark.asyncio
async def test_consensus_pr6_sync_resp_malformed_qc_reject_gate() -> None:
    # NOTE: if slow boots, export GLYPHCHAIN_TEST_NODE_READY_TIMEOUT_S=240
    nodes = await start_n_nodes(2, base_port=18490, chain_id="glyphchain-dev")
    try:
        dst = nodes[0]
        src = nodes[1]

        st0 = await _get_status(dst)
        fh0 = int(st0.get("finalized_height") or 0)
        last0 = st0.get("last_qc")

        # malformed last_qc (missing required fields / wrong types)
        bad_payload = {
            "finalized_height": max(1, fh0),
            "last_qc": {"height": "nope"},  # intentionally invalid
            "round": 0,
        }

        rr = await http_post(dst.base_url, "/api/p2p/sync_resp", _mk_env(src=src, payload=bad_payload), timeout_s=10.0)

        stc = int(rr.get("status") or 0)
        assert stc in (200, 400, 403), rr
        assert stc != 500, rr

        # state must not regress/change due to malformed QC
        st1 = await _get_status(dst)
        assert int(st1.get("finalized_height") or 0) >= fh0, "finalized_height regressed after malformed sync_resp"
        assert st1.get("last_qc") == last0, "last_qc changed after malformed sync_resp"

    finally:
        await stop_nodes(nodes)