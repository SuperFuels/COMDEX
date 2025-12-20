import os
import time
import pytest
pytestmark = [pytest.mark.integration, pytest.mark.glyphchain]

from backend.tests.helpers import start_n_nodes, stop_nodes, http_post


@pytest.mark.integration
@pytest.mark.asyncio
async def test_p2p_status_sync_req_response_cache_returns_identical_payload() -> None:
    """
    Gate:
      - send STATUS twice with same msg_id => second response has cached=True + dedup=True
      - send SYNC_REQ twice with same msg_id => second response has cached=True + dedup=True
    """
    # make cache deterministic + fast
    os.environ["P2P_RESP_CACHE_TTL_MS"] = "2000"
    os.environ["P2P_RESP_CACHE_MAX"] = "2048"
    os.environ["P2P_DEDUP_TTL_MS"] = "15000"
    os.environ["P2P_DEDUP_MAX"] = "20000"

    nodes = await start_n_nodes(2)
    try:
        a = nodes[0]
        b = nodes[1]

        # --- STATUS ---
        msg_id = f"status-test-{int(time.time() * 1000)}"
        env = {
            "type": "STATUS",
            "from_node_id": a["node_id"],
            "from_val_id": a["val_id"],
            "chain_id": a["chain_id"],
            "ts_ms": float(time.time() * 1000.0),
            "payload": {"msg_id": msg_id},
            "hops": 0,
        }

        r1 = await http_post(b["base_url"], "/api/p2p/status", env)
        assert r1.get("ok") is True
        assert "payload" in r1 and isinstance(r1["payload"], dict)
        assert not r1.get("cached", False)

        r2 = await http_post(b["base_url"], "/api/p2p/status", env)
        assert r2.get("ok") is True
        assert r2.get("cached") is True
        assert r2.get("dedup") is True
        assert r2.get("payload") == r1.get("payload")

        # --- SYNC_REQ ---
        msg_id2 = f"syncreq-test-{int(time.time() * 1000)}"
        env2 = {
            "type": "SYNC_REQ",
            "from_node_id": a["node_id"],
            "from_val_id": a["val_id"],
            "chain_id": a["chain_id"],
            "ts_ms": float(time.time() * 1000.0),
            "payload": {"msg_id": msg_id2},
            "hops": 0,
        }

        s1 = await http_post(b["base_url"], "/api/p2p/sync_req", env2)
        assert s1.get("ok") is True
        assert "payload" in s1 and isinstance(s1["payload"], dict)
        assert not s1.get("cached", False)

        s2 = await http_post(b["base_url"], "/api/p2p/sync_req", env2)
        assert s2.get("ok") is True
        assert s2.get("cached") is True
        assert s2.get("dedup") is True
        assert s2.get("payload") == s1.get("payload")

    finally:
        await stop_nodes(nodes)