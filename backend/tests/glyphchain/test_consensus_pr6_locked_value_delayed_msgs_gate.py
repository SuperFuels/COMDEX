# backend/tests/glyphchain/test_consensus_pr6_locked_value_delayed_msgs_gate.py
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional
import re
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.glyphchain]

from backend.tests.helpers import start_n_nodes, stop_nodes, http_get, http_post
from backend.modules.p2p.crypto_ed25519 import canonical_p2p_sign_bytes, sign_ed25519

_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")


def _p2p_priv_hex(n) -> str:
    return (
        (getattr(n, "p2p_privkey_hex", None) or "")
        or (getattr(n, "privkey_hex", None) or "")
        or (getattr(n, "priv_key_hex", None) or "")
    ).strip()


def _sign_payload(node, *, msg_type: str, payload: Dict[str, Any]) -> str:
    priv = _p2p_priv_hex(node)
    assert priv, (
        f"node missing p2p privkey hex (can’t sign): "
        f"node_id={getattr(node,'node_id',None)} val_id={getattr(node,'val_id',None)}"
    )
    msg = canonical_p2p_sign_bytes(msg_type=msg_type, chain_id=node.chain_id, payload=payload)
    sig = sign_ed25519(priv, msg)
    assert isinstance(sig, str) and sig.strip(), f"sign_ed25519 returned empty/non-str: {sig!r}"
    sig = sig.strip()
    assert _HEX_RE.match(sig), f"signature is not hex (would 500 server-side): {sig!r}"
    return sig.lower()


def _now_ms() -> float:
    return float(time.time() * 1000.0)


def _canon_block_id(height: int, round: int, proposer: str) -> str:
    return f"h{int(height)}-r{int(round)}-P{str(proposer)}"


def _leader_for(validators: list[str], height: int, round: int) -> Optional[str]:
    ids = [str(x) for x in (validators or []) if str(x)]
    if not ids:
        return None
    idx = (int(height) - 1 + int(round)) % len(ids)
    return ids[idx]


def _mk_env(*, src, msg_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": str(msg_type),
        "from_node_id": src.node_id,
        "from_val_id": src.val_id,
        "chain_id": src.chain_id,
        "ts_ms": _now_ms(),
        "payload": payload,
        "hops": 0,
    }


async def _get_status(node) -> Dict[str, Any]:
    r = await http_get(node.base_url, "/api/p2p/consensus_status", timeout_s=6.0)
    assert int(r.get("status") or 0) == 200, f"status fetch failed: {r}"
    j = r.get("json") or {}
    assert isinstance(j, dict)
    return j


async def _warm_and_assert_peers(dst, src_nodes) -> None:
    r = await http_get(dst.base_url, "/api/p2p/peers", timeout_s=6.0)
    assert int(r.get("status") or 0) == 200, f"peers fetch failed: {r}"
    j = r.get("json") or {}
    assert isinstance(j, dict) and j.get("ok") is True, f"bad peers response: {r}"
    peers = j.get("peers") or []
    assert isinstance(peers, list)

    by_node: dict[str, dict[str, Any]] = {}
    for p in peers:
        if isinstance(p, dict) and p.get("node_id"):
            by_node[str(p["node_id"])] = p

    for s in src_nodes:
        rec = by_node.get(str(s.node_id))
        assert isinstance(rec, dict), f"dst missing peer record for {s.node_id}: peers={peers}"
        assert bool(rec.get("hello_ok")), f"dst peer not hello_ok for {s.node_id}: {rec}"
        assert str(rec.get("pubkey_hex") or "").strip(), f"dst peer missing pubkey_hex for {s.node_id}: {rec}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_consensus_pr6_locked_value_delayed_msgs_gate() -> None:
    nodes = await start_n_nodes(4, base_port=18080, chain_id="glyphchain-dev")
    try:
        dst = nodes[3]
        srcA, srcB, srcC = nodes[0], nodes[1], nodes[2]

        await _warm_and_assert_peers(dst, [srcA, srcB, srcC])

        st0 = await _get_status(dst)
        validators = list(st0.get("validators") or [])
        assert validators, f"no validators in status: {st0}"

        # Pick a future height where leader(round=0) is srcA
        base_fh = int(st0.get("finalized_height") or 0)
        target_h: Optional[int] = None
        for hh in range(base_fh + 25, base_fh + 200):
            if _leader_for(validators, hh, 0) == srcA.val_id:
                target_h = hh
                break
        assert target_h is not None, f"could not find height led by {srcA.val_id} in search window"
        h = int(target_h)
        r0 = 0

        leader0 = _leader_for(validators, h, r0)
        assert leader0 == srcA.val_id
        blockA = _canon_block_id(h, r0, leader0)

        # Step 0: deliver canonical PROPOSAL A
        pA: Dict[str, Any] = {
            "height": h,
            "round": r0,
            "proposer": leader0,
            "block_id": blockA,
            "block": {},
            "ts_ms": _now_ms(),
        }
        pA["sig_hex"] = _sign_payload(srcA, msg_type="PROPOSAL", payload=pA)
        rr = await http_post(dst.base_url, "/api/p2p/proposal", _mk_env(src=srcA, msg_type="PROPOSAL", payload=pA), timeout_s=6.0)
        assert int(rr.get("status") or 0) == 200, f"proposal A send failed: {rr}"

        # Step 1: create PREVOTE quorum at (h,r0) for A on dst -> dst locks on A (via its PRECOMMIT)
        for src in (srcA, srcB, srcC):
            v: Dict[str, Any] = {
                "height": h,
                "round": r0,
                "voter": src.val_id,
                "vote_type": "PREVOTE",
                "block_id": blockA,
                "ts_ms": _now_ms(),
            }
            v["sig_hex"] = _sign_payload(src, msg_type="VOTE", payload=v)
            rr = await http_post(dst.base_url, "/api/p2p/vote", _mk_env(src=src, msg_type="VOTE", payload=v), timeout_s=6.0)
            assert int(rr.get("status") or 0) == 200, f"prevote send failed: {rr}"

        # Step 2: wait until dst is LOCKED on A
        deadline = time.time() + 20.0
        while True:
            st = await _get_status(dst)
            lock = st.get("lock") or {}
            if (
                isinstance(lock, dict)
                and int(lock.get("height") or 0) == h
                and str(lock.get("block_id") or "") == blockA
            ):
                break
            if time.time() > deadline:
                raise AssertionError(f"dst never locked on A at height {h}: {st}")
            await asyncio.sleep(0.25)

        # Sanity: should NOT be finalized at h (we never provide PRECOMMIT quorum)
        st_locked = await _get_status(dst)
        assert int(st_locked.get("finalized_height") or 0) < h, f"unexpected finalize at h={h}: {st_locked}"

        # Step 3 (PR6.2): higher-round conflicting proposal is ALLOWED (stored/observed)
        r1 = 1
        leader1 = _leader_for(validators, h, r1)
        assert leader1 is not None
        blockB = _canon_block_id(h, r1, leader1)

        pB: Dict[str, Any] = {
            "height": h,
            "round": r1,
            "proposer": leader1,
            "block_id": blockB,
            "block": {},
            "ts_ms": _now_ms(),
        }
        pB["sig_hex"] = _sign_payload(srcA, msg_type="PROPOSAL", payload=pB)
        rr = await http_post(dst.base_url, "/api/p2p/proposal", _mk_env(src=srcA, msg_type="PROPOSAL", payload=pB), timeout_s=6.0)
        assert int(rr.get("status") or 0) == 200, f"expected accept/store higher-round proposal under PR6.2, got: {rr}"

        # Step 4 (core safety): a conflicting PRECOMMIT at higher round WITHOUT a PREVOTE quorum must be rejected.
        # (This is the “delayed msgs can’t finalize behind fork-choice/lock rules” invariant.)
        precommitB: Dict[str, Any] = {
            "height": h,
            "round": r1,
            "voter": srcA.val_id,
            "vote_type": "PRECOMMIT",
            "block_id": blockB,
            "ts_ms": _now_ms(),
        }
        precommitB["sig_hex"] = _sign_payload(srcA, msg_type="VOTE", payload=precommitB)
        rr = await http_post(dst.base_url, "/api/p2p/vote", _mk_env(src=srcA, msg_type="VOTE", payload=precommitB), timeout_s=6.0)
        assert int(rr.get("status") or 0) == 400, f"expected reject precommit without prevote quorum, got: {rr}"

        # Step 5: invariant — no finalize at height h
        st_end = await _get_status(dst)
        assert int(st_end.get("finalized_height") or 0) < h, f"unexpected finalize at h={h}: {st_end}"

        # Also ensure lock is still at height h (may remain A or relock to B if a real prevote quorum occurs)
        lock = st_end.get("lock") or {}
        assert isinstance(lock, dict)
        assert int(lock.get("height") or 0) == h, f"expected lock height to remain h={h}, got: {st_end}"

    finally:
        await stop_nodes(nodes)