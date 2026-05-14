from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Dict, Optional
import re
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.glyphchain]

from backend.tests.helpers import start_n_nodes, stop_nodes, http_get, http_post
from backend.modules.p2p.crypto_ed25519 import canonical_p2p_sign_bytes, sign_ed25519

_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")


def _now_ms() -> float:
    return float(time.time() * 1000.0)


def _p2p_priv_hex(n) -> str:
    return (
        (getattr(n, "p2p_privkey_hex", None) or "")
        or (getattr(n, "privkey_hex", None) or "")
        or (getattr(n, "priv_key_hex", None) or "")
    ).strip()


def _sign_payload(node, *, msg_type: str, payload: Dict[str, Any]) -> str:
    priv = _p2p_priv_hex(node)
    assert priv, f"missing p2p privkey hex for node_id={getattr(node,'node_id',None)}"
    msg = canonical_p2p_sign_bytes(msg_type=msg_type, chain_id=node.chain_id, payload=payload)
    sig = sign_ed25519(priv, msg)
    assert isinstance(sig, str) and sig.strip(), f"sign_ed25519 returned empty/non-str: {sig!r}"
    sig = sig.strip().lower()
    assert _HEX_RE.match(sig), f"sig not hex: {sig!r}"
    return sig


async def _get_status(node) -> Dict[str, Any]:
    r = await http_get(node.base_url, "/api/p2p/consensus_status", timeout_s=8.0)
    assert int(r.get("status") or 0) == 200, r
    j = r.get("json") or {}
    assert isinstance(j, dict)
    return j


async def _warm_and_assert_peer(dst, src) -> None:
    # ensure HELLO is visible so sig verification has a pubkey
    deadline = time.time() + 20.0
    while time.time() < deadline:
        r = await http_get(dst.base_url, "/api/p2p/peers", timeout_s=6.0)
        if int(r.get("status") or 0) != 200:
            await asyncio.sleep(0.25)
            continue
        j = r.get("json") or {}
        peers = (j or {}).get("peers") or []
        for p in peers:
            if isinstance(p, dict) and str(p.get("node_id")) == str(src.node_id):
                if p.get("hello_ok") and str(p.get("pubkey_hex") or "").strip():
                    return
        await asyncio.sleep(0.25)
    raise AssertionError(f"dst never saw hello_ok+pubkey for src={src.node_id}")


@pytest.mark.asyncio
async def test_p2p_ingress_backpressure_gate() -> None:
    # Small ingress limits so a dup flood provokes drops.
    env_overrides = {
        "P2P_LANE_MAX_QUEUE_VOTE": "32",
        "P2P_LANE_MAX_INFLIGHT_VOTE": "1",
        "P2P_LANE_DUP_LRU_VOTE": "256",
        "P2P_LANE_YIELD_EVERY_VOTE": "16",
        "P2P_LANE_DROP_POLICY": "drop_new",
    }

    # Apply overrides for child processes spawned by start_n_nodes()
    old_env: Dict[str, Optional[str]] = {k: os.environ.get(k) for k in env_overrides.keys()}
    os.environ.update(env_overrides)

    nodes = None
    try:
        nodes = await start_n_nodes(4, base_port=18280, chain_id="glyphchain-dev")
        dst = nodes[0]
        src = nodes[1]

        await _warm_and_assert_peer(dst, src)

        st0 = await _get_status(dst)
        base_fh = int(st0.get("finalized_height") or 0)
        validators = list(st0.get("validators") or [])
        assert validators, f"no validators: {st0}"

        # pick a height within the future-height window
        h = int(base_fh + 2)
        r0 = 0
        leader0 = validators[(h - 1 + r0) % len(validators)]
        block_id = f"h{h}-r{r0}-P{leader0}"

        # Fixed ts_ms so msg_id (if derived) and signature stay constant across dup flood.
        ts_ms = _now_ms()

        vote: Dict[str, Any] = {
            "height": h,
            "round": r0,
            "voter": src.val_id,
            "vote_type": "PREVOTE",
            "block_id": block_id,
            "ts_ms": ts_ms,
        }
        vote["sig_hex"] = _sign_payload(src, msg_type="VOTE", payload=vote)

        env = {
            "type": "VOTE",
            "from_node_id": src.node_id,
            "from_val_id": src.val_id,
            "chain_id": src.chain_id,
            "ts_ms": ts_ms,
            "payload": vote,
            "hops": 0,
        }

        # Flood duplicates; handler should not 500 even under drops.
        N = 1000
        for _ in range(N):
            rr = await http_post(dst.base_url, "/api/p2p/vote", env, timeout_s=10.0)
            assert int(rr.get("status") or 0) in (200, 400, 403), rr
            assert int(rr.get("status") or 0) != 500, rr

        # Liveness: finalized height should keep moving.
        deadline = time.time() + 20.0
        moved = False
        while time.time() < deadline:
            st = await _get_status(dst)
            if int(st.get("finalized_height") or 0) > base_fh:
                moved = True
                break
            await asyncio.sleep(0.25)
        assert moved, f"dst stopped finalizing under flood (base_fh={base_fh})"

        # Drops should be observable once you’ve wired p2p_ingress snapshot into status().
        st_end = await _get_status(dst)
        ing = (st_end.get("p2p_ingress") or {}).get("lanes") or {}
        vote_lane = (ing.get("vote") or {})
        ctr = (vote_lane.get("counters") or {})
        dropped_dup = int(ctr.get("dropped_dup") or 0)
        dropped_full = int(ctr.get("dropped_full") or 0)

        assert (dropped_dup + dropped_full) > 0, f"expected drops under dup flood, got: {vote_lane}"

    finally:
        # restore env
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

        if nodes is not None:
            await stop_nodes(nodes)