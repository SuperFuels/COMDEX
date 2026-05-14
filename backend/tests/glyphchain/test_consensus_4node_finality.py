# backend/tests/glyphchain/test_consensus_4node_finality.py
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List

import pytest

from backend.tests.helpers import start_n_nodes, stop_nodes, http_get


pytestmark = [pytest.mark.integration, pytest.mark.glyphchain, pytest.mark.asyncio]


def _status_line(st: Dict[str, Any]) -> str:
    return (
        f"fh={int(st.get('finalized_height') or 0)} "
        f"h={int(st.get('height') or 0)} "
        f"r={int(st.get('round') or 0)} "
        f"leader={st.get('leader')!s} "
        f"have_prop={bool(st.get('have_proposal'))} "
        f"hello_ok={_peers_hello_ok_count(st)}"
    )


def _peers_hello_ok_count(_st: Dict[str, Any]) -> str:
    # consensus_status doesn’t include peers; keep this placeholder stable for logs
    return "n/a"


async def _get_status(base_url: str) -> Dict[str, Any]:
    r = await http_get(base_url, "/api/p2p/consensus_status", timeout_s=8.0)
    assert int(r.get("status") or 0) == 200, f"consensus_status failed: {r}"
    j = r.get("json") or {}
    assert isinstance(j, dict), f"bad consensus_status json: {r}"
    return j


async def _wait_peers_up(nodes: List[Any], timeout_s: float = 60.0) -> None:
    deadline = time.time() + timeout_s
    last: Any = None
    while time.time() < deadline:
        ok = True
        for n in nodes:
            r = await http_get(n.base_url, "/api/p2p/peers", timeout_s=6.0)
            if int(r.get("status") or 0) != 200:
                ok = False
                last = r
                break
            j = r.get("json") or {}
            if not (isinstance(j, dict) and j.get("ok") is True):
                ok = False
                last = j
                break
        if ok:
            return
        await asyncio.sleep(0.25)
    raise RuntimeError(f"p2p stack not ready; last={last!r}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_consensus_4node_finalizes_deterministically() -> None:
    """
    Deterministic multi-node finality smoke gate.

    NOTE: This intentionally uses the shared integration harness (start_n_nodes),
    because it’s responsible for deterministic per-node identities + HELLO mesh,
    which are required now that P2P lanes can be strictly enforced (403 otherwise).
    """
    chain_id = "glyphchain-dev"
    K = 8

    nodes = await start_n_nodes(4, base_port=18101, chain_id=chain_id)
    try:
        await _wait_peers_up(nodes, timeout_s=90.0)

        deadline = time.time() + 180.0
        last_statuses: List[Dict[str, Any]] = []

        while time.time() < deadline:
            last_statuses = []
            hs: List[int] = []
            for n in nodes:
                st = await _get_status(n.base_url)
                last_statuses.append(st)
                hs.append(int(st.get("finalized_height") or 0))

            # "good enough" for this gate: at least one node finalizes through K
            # (stronger all-nodes convergence is covered by other sync/catchup gates)
            if max(hs) >= K:
                return

            await asyncio.sleep(0.25)

        diag = "\n".join(
            f"{getattr(n, 'base_url', '?')}: {_status_line(st)}"
            for n, st in zip(nodes, last_statuses)
        )
        raise RuntimeError(f"did not finalize to K={K}; statuses:\n{diag}")

    finally:
        await stop_nodes(nodes)