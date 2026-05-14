from __future__ import annotations

from typing import Any, Dict
import pytest
pytestmark = [pytest.mark.integration, pytest.mark.glyphchain]

from backend.tests.helpers import start_n_nodes, stop_nodes, http_get


@pytest.mark.integration
@pytest.mark.asyncio
async def test_p2p_hello_coverage_gate() -> None:
    nodes = await start_n_nodes(3, base_port=18080, chain_id="glyphchain-dev")
    try:
        for n in nodes:
            r = await http_get(n.base_url, "/api/p2p/peers", timeout_s=6.0)
            assert int(r.get("status") or 0) == 200, f"/peers failed: {r}"
            j = r.get("json")
            assert isinstance(j, dict) and j.get("ok") is True, f"bad /peers: {r}"

            peers = j.get("peers") or []
            assert isinstance(peers, list)

            by_node: Dict[str, Dict[str, Any]] = {}
            for p in peers:
                if isinstance(p, dict) and p.get("node_id"):
                    by_node[str(p["node_id"])] = p

            # Require that every OTHER node is hello_ok + has pubkey_hex
            for other in nodes:
                if other.node_id == n.node_id:
                    continue
                rec = by_node.get(other.node_id)
                assert isinstance(rec, dict), f"missing peer record for {other.node_id} on {n.node_id}: {peers}"
                assert bool(rec.get("hello_ok")) is True, f"hello_ok not true for {other.node_id} on {n.node_id}: {rec}"
                assert (rec.get("pubkey_hex") or "").strip(), f"missing pubkey_hex for {other.node_id} on {n.node_id}: {rec}"

    finally:
        await stop_nodes(nodes)