# backend/tests/test_consensus_pr4_restart_catchup_gate.py
from __future__ import annotations
import pytest
pytestmark = [pytest.mark.integration, pytest.mark.glyphchain]
import asyncio
import json
import os
import signal
import socket
import subprocess
import time
from typing import Any, Dict, List

import pytest

from backend.tests.helpers import (
    NodeProc,
    http_get,
    http_post,
    start_n_nodes,
    stop_nodes,
)

# -------------------------
# small utilities
# -------------------------


def _now_ms() -> float:
    return float(time.time() * 1000.0)


def _tcp_listening(host: str, port: int, timeout_s: float = 0.25) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout_s):
            return True
    except Exception:
        return False


async def _wait_ready(base_url: str, port: int, timeout_s: float = 45.0) -> None:
    deadline = time.time() + float(timeout_s)
    while time.time() < deadline:
        if _tcp_listening("127.0.0.1", port, timeout_s=0.25):
            try:
                r = await http_get(base_url, "/api/p2p/peers", timeout_s=2.0)
                if int(r.get("status") or 0) == 200 and isinstance(r.get("json"), dict) and r["json"].get("ok"):
                    return
            except Exception:
                pass
        await asyncio.sleep(0.2)
    raise RuntimeError(f"node not ready: {base_url}")


async def _p2p_status(target: NodeProc, caller: NodeProc) -> Dict[str, Any]:
    env = {
        "type": "STATUS",
        "chain_id": getattr(caller, "chain_id", "") or os.getenv("GLYPHCHAIN_CHAIN_ID", "glyphchain-dev"),
        "from_node_id": caller.node_id,
        "from_val_id": caller.val_id,
        "ts_ms": _now_ms(),
        "payload": {"want": "status"},
        "hops": 0,
    }
    r = await http_post(target.base_url, "/api/p2p/status", env, timeout_s=6.0)
    if int(r.get("status") or 0) != 200 or not isinstance(r.get("json"), dict):
        raise RuntimeError(f"bad /api/p2p/status response: {r}")
    j = r["json"]
    if j.get("ok") is not True or not isinstance(j.get("payload"), dict):
        raise RuntimeError(f"bad /api/p2p/status payload: {j}")
    return j["payload"]


async def _p2p_block_req(target: NodeProc, caller: NodeProc, height: int) -> Dict[str, Any]:
    env = {
        "type": "BLOCK_REQ",
        "chain_id": getattr(caller, "chain_id", "") or os.getenv("GLYPHCHAIN_CHAIN_ID", "glyphchain-dev"),
        "from_node_id": caller.node_id,
        "from_val_id": caller.val_id,
        "ts_ms": _now_ms(),
        "payload": {"height": int(height), "want": "block"},
        "hops": 0,
    }
    r = await http_post(target.base_url, "/api/p2p/block_req", env, timeout_s=30.0)
    if int(r.get("status") or 0) != 200 or not isinstance(r.get("json"), dict):
        raise RuntimeError(f"bad /api/p2p/block_req response: {r}")
    return r["json"]


def _app_import() -> str:
    env = (os.getenv("GLYPHCHAIN_ASGI_APP", "") or "").strip()
    return env or "backend.main:app"


def _restart_node_sync(node: NodeProc, *, validators_env: str, peers_json: List[Dict[str, Any]]) -> None:
    """
    Restart the same node (same port/state_dir/node_id/val_id).
    Mutates node.proc in-place.

    CRITICAL:
      - re-seed peer_store via P2P_PEERS_JSON so catchup can contact peers
      - re-set CHAIN_SIM_DB_PATH so restarted node reads the same sqlite
      - re-set GLYPHCHAIN_P2P_PRIVKEY_HEX so bootstrap HELLO can sign + peers accept SYNC lane
    """
    # normalize uvicorn lifespan arg
    lifespan = (os.getenv("GLYPHCHAIN_TEST_UVICORN_LIFESPAN", "off") or "off").strip().lower()
    if lifespan not in ("off", "on", "auto"):
        lifespan = "off"

    # reuse existing state_dir; do NOT delete
    log_path = os.path.join(node.state_dir, "uvicorn.restart.log")
    log_fp = open(log_path, "a", buffering=1, encoding="utf-8")

    env = dict(os.environ)
    env["GLYPHCHAIN_CHAIN_ID"] = getattr(node, "chain_id", "") or os.getenv("GLYPHCHAIN_CHAIN_ID", "glyphchain-dev")
    env["GLYPHCHAIN_NODE_ID"] = node.node_id
    env["GLYPHCHAIN_SELF_VAL_ID"] = node.val_id
    env["GLYPHCHAIN_BASE_URL"] = node.base_url
    env["GLYPHCHAIN_STATE_DIR"] = node.state_dir

    # ✅ IMPORTANT: keep the same per-node sqlite DB on restart
    env["CHAIN_SIM_DB_PATH"] = os.path.join(node.state_dir, "chain_sim.sqlite3")

    # ✅ IMPORTANT: keep the same deterministic per-node P2P signing key on restart
    if getattr(node, "p2p_privkey_hex", ""):
        env["GLYPHCHAIN_P2P_PRIVKEY_HEX"] = node.p2p_privkey_hex

    # keep validator env consistent with ValidatorSet.from_env()
    env["GLYPHCHAIN_VALIDATORS"] = validators_env
    env["GLYPHCHAIN_VALIDATOR_SET"] = validators_env
    env["CONSENSUS_VALIDATORS"] = validators_env

    # seed peers on restart so sync/fill can fetch blocks
    env["P2P_PEERS_JSON"] = json.dumps(peers_json)

    # force consensus on
    env["GLYPHCHAIN_CONSENSUS_ENABLE"] = "1"

    cmd = [
        "python",
        "-m",
        "uvicorn",
        _app_import(),
        "--host",
        "127.0.0.1",
        "--port",
        str(int(node.port)),
        "--log-level",
        "warning",
        "--no-access-log",
        "--lifespan",
        lifespan,
    ]

    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=log_fp,
        stderr=subprocess.STDOUT,
        text=True,
    )

    node.proc = proc
    try:
        setattr(node, "log_path", log_path)
        setattr(node, "_log_fp", log_fp)
    except Exception:
        pass

# -------------------------
# the gate
# -------------------------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_consensus_pr4_restart_catchup_gate() -> None:
    """
    Gate:
      - run 3-node cluster until it finalizes
      - kill -9 one node mid-run (it misses broadcasts)
      - remaining 2 keep finalizing
      - restart killed node (same identity + state dir)
      - restarted node deterministically catches up to finalized tip via SYNC_REQ + BLOCK_REQ fill
    """
    nodes: List[NodeProc] = []
    try:
        nodes = await start_n_nodes(3, base_port=18080, chain_id="glyphchain-dev")
        validators_env = ",".join([f"{n.val_id}:1" for n in nodes])

        # deterministic peer seed for restarts
        peers_json: List[Dict[str, Any]] = [
            {"node_id": n.node_id, "base_url": n.base_url, "val_id": n.val_id, "role": "peer"} for n in nodes
        ]

        a, b, c = nodes[0], nodes[1], nodes[2]

        # wait until we have some finalized height > 0
        deadline = time.time() + 60.0
        base_fh = 0
        while time.time() < deadline:
            st = await _p2p_status(a, a)
            base_fh = int(st.get("finalized_height") or 0)
            if base_fh >= 1:
                break
            await asyncio.sleep(0.25)
        assert base_fh >= 1, f"expected finalized_height>=1, got {base_fh}"

        # kill -9 one node
        try:
            os.kill(int(c.proc.pid), signal.SIGKILL)
        except Exception:
            try:
                c.proc.kill()
            except Exception:
                pass

        await asyncio.sleep(0.3)

        # remaining cluster should continue finalizing
        target_fh = base_fh + 2
        deadline = time.time() + 90.0
        cur = base_fh
        while time.time() < deadline:
            st = await _p2p_status(a, a)
            cur = int(st.get("finalized_height") or 0)
            if cur >= target_fh:
                break
            await asyncio.sleep(0.35)
        assert cur >= target_fh, f"cluster did not advance: base={base_fh} cur={cur} target={target_fh}"

        # restart killed node (seed peers!)
        _restart_node_sync(c, validators_env=validators_env, peers_json=peers_json)
        await _wait_ready(c.base_url, c.port, timeout_s=60.0)

        # restarted node should catch up
        deadline = time.time() + 120.0
        caught = 0
        while time.time() < deadline:
            st_c = await _p2p_status(c, c)
            caught = int(st_c.get("finalized_height") or 0)
            if caught >= cur:
                break
            await asyncio.sleep(0.35)
        assert caught >= cur, f"restart node did not catch up: got={caught} want>={cur}"

        # and it should have the finalized-tip block locally
        j = await _p2p_block_req(c, c, height=cur)
        assert j.get("ok") is True, f"expected ok:true from block_req, got: {j}"
        blk = j.get("block")
        assert isinstance(blk, dict), f"expected block dict, got: {type(blk)}"
        assert int(blk.get("height") or 0) == int(cur), f"block height mismatch: {blk.get('height')} vs {cur}"

    finally:
        if nodes:
            # ---- DEBUG DUMP (runs even on failure, before teardown) ----
            try:
                print("\n=== DEBUG consensus_status + peers ===")
                for n in nodes:
                    cs = await http_get(n.base_url, "/api/p2p/consensus_status", timeout_s=2.0)
                    ps = await http_get(n.base_url, "/api/p2p/peers", timeout_s=2.0)
                    print(n.base_url, "consensus_status=", cs.get("json"))
                    print(n.base_url, "peers=", ps.get("json"))
            except Exception as e:
                print("[debug dump failed]", e)

            await stop_nodes(nodes)