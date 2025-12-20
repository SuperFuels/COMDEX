# backend/tests/glyphchain/test_consensus_pr6_lock_unlock_across_rounds_gate.py
from __future__ import annotations

import asyncio
import contextlib
import os
import socket
import time
from typing import Any, Dict, List, Tuple

import pytest

from backend.modules.p2p.crypto_ed25519 import canonical_p2p_sign_bytes, sign_ed25519
from backend.tests.helpers import http_get, http_post, start_n_nodes, stop_nodes

pytestmark = [pytest.mark.integration, pytest.mark.glyphchain]


@contextlib.contextmanager
def _tmp_env(**kvs: str):
    old = {k: os.environ.get(k) for k in kvs}
    for k, v in kvs.items():
        os.environ[k] = str(v)
    try:
        yield
    finally:
        for k, prev in old.items():
            if prev is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = prev


def _now_ms() -> float:
    return float(time.time() * 1000.0)


def _canon_block_id(h: int, r: int, proposer: str) -> str:
    return f"h{int(h)}-r{int(r)}-P{proposer}"


def _leader_for(ids: List[str], h: int, r: int) -> str:
    n = len(ids)
    idx = (int(h) - 1 + int(r)) % n
    return str(ids[idx])


def _mk_env(*, src, msg_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": msg_type,
        "from_node_id": src.node_id,
        "from_val_id": src.val_id,
        "chain_id": src.chain_id,
        "ts_ms": _now_ms(),
        "payload": payload,
        "hops": 0,
    }


async def _post_signed(
    base_url: str,
    path: str,
    *,
    src,
    msg_type: str,
    chain_id: str,
    payload_wo_sig: Dict[str, Any],
    timeout_s: float = 8.0,
) -> Dict[str, Any]:
    sig_msg = canonical_p2p_sign_bytes(msg_type=msg_type, chain_id=chain_id, payload=payload_wo_sig)
    payload = dict(payload_wo_sig)
    payload["sig_hex"] = sign_ed25519(src.p2p_privkey_hex, sig_msg)
    return await http_post(base_url, path, _mk_env(src=src, msg_type=msg_type, payload=payload), timeout_s=timeout_s)


def _pick_free_port_span(n: int, *, start: int = 18500, end: int = 26000) -> int:
    """
    Find a base port such that [base, base+n) are all bindable on 127.0.0.1.
    Avoids flakes from lingering processes / port collisions.
    """
    def _can_bind(p: int) -> bool:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", p))
            return True
        except OSError:
            return False
        finally:
            try:
                s.close()
            except Exception:
                pass

    for base in range(start, end - n):
        ok = True
        for p in range(base, base + n):
            if not _can_bind(p):
                ok = False
                break
        if ok:
            return base
    raise RuntimeError(f"could not find free port span of {n} ports in [{start},{end})")


async def _wait_ok(base_url: str, path: str, *, timeout_s: float = 240.0) -> None:
    deadline = time.time() + timeout_s
    last: Any = None
    while time.time() < deadline:
        try:
            r = await http_get(base_url, path, timeout_s=6.0)
            if int(r.get("status") or 0) == 200:
                return
            last = r
        except Exception as e:
            last = repr(e)
        await asyncio.sleep(0.10)
    raise RuntimeError(f"service not ready: {base_url}{path} last={last!r}")


async def _pick_live_hr(
    *,
    dst,
    peers,
    timeout_s: float = 30.0,
) -> Tuple[int, int, int, List[str], str, str]:
    """
    Pick a *stable* live (h,r0) window where:
      - h > finalized_height
      - have_proposal == False
      - leader(h,r0) is one of `peers`
      - leader(h,r0+1) is one of `peers`
      - (h,r0,have_proposal) is stable across two polls (reduces race w/ engine tick)
    """
    peer_ids = {p.val_id for p in peers}
    deadline = time.time() + timeout_s
    last: Any = None
    prev_key: Any = None
    stable_hits = 0

    while time.time() < deadline:
        st = await http_get(dst.base_url, "/api/p2p/consensus_status", timeout_s=8.0)
        if int(st.get("status") or 0) != 200:
            last = st
            await asyncio.sleep(0.05)
            continue

        j = st.get("json") or {}
        last = j

        ids = j.get("validators") or []
        if not (isinstance(ids, list) and ids):
            await asyncio.sleep(0.05)
            continue
        ids_s = [str(x) for x in ids]

        fh = int(j.get("finalized_height") or 0)
        h = int(j.get("height") or 0)
        r0 = int(j.get("round") or 0)
        have_prop = bool(j.get("have_proposal") is True)

        if h <= fh:
            await asyncio.sleep(0.05)
            continue
        if have_prop:
            await asyncio.sleep(0.05)
            continue

        key = (h, r0, have_prop)
        if key == prev_key:
            stable_hits += 1
        else:
            stable_hits = 0
            prev_key = key

        if stable_hits < 1:
            await asyncio.sleep(0.08)
            continue

        proposer0 = _leader_for(ids_s, h, r0)
        if proposer0 not in peer_ids:
            await asyncio.sleep(0.05)
            continue

        rB = r0 + 1
        proposerB = _leader_for(ids_s, h, rB)
        if proposerB not in peer_ids:
            await asyncio.sleep(0.05)
            continue

        return h, r0, rB, ids_s, proposer0, proposerB

    raise AssertionError(f"could not pick stable LIVE (h,r) window; last={last!r}")


async def _wait_for_observation(
    *,
    dst,
    pred,
    timeout_s: float,
    poll_s: float = 0.05,
) -> Dict[str, Any]:
    deadline = time.time() + timeout_s
    last: Dict[str, Any] = {}
    while time.time() < deadline:
        st = await http_get(dst.base_url, "/api/p2p/consensus_status", timeout_s=8.0)
        if int(st.get("status") or 0) != 200:
            await asyncio.sleep(poll_s)
            continue
        j = st.get("json") or {}
        if isinstance(j, dict):
            last = j
        if pred(last):
            return last
        await asyncio.sleep(poll_s)
    raise RuntimeError(f"timeout waiting for observation; last={last!r}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_consensus_pr6_lock_unlock_across_rounds_gate() -> None:
    base_port = _pick_free_port_span(4, start=18500, end=26000)

    # Slow the background engine enough to reduce "advanced past injected height" flakes,
    # without stalling state transitions entirely.
    with _tmp_env(
        CONSENSUS_TICK_MS=os.getenv("CONSENSUS_TICK_MS", "800"),
        CONSENSUS_ROUND_TIMEOUT_MS=os.getenv("CONSENSUS_ROUND_TIMEOUT_MS", "6000"),
        CONSENSUS_SYNC_EVERY_MS=os.getenv("CONSENSUS_SYNC_EVERY_MS", "6000"),
        CONSENSUS_PROPOSAL_REBCAST_S=os.getenv("CONSENSUS_PROPOSAL_REBCAST_S", "2.0"),
    ):
        nodes = await start_n_nodes(4, base_port=base_port, chain_id="glyphchain-dev")

    try:
        # Extra readiness (start_n_nodes can return while some routes are still warming up)
        for n in nodes:
            await _wait_ok(n.base_url, "/api/p2p/peers", timeout_s=240.0)
            await _wait_ok(n.base_url, "/api/p2p/consensus_status", timeout_s=240.0)

        dst = nodes[1]
        peers = [nodes[0], nodes[2], nodes[3]]
        peer_by_val = {p.val_id: p for p in peers}

        attempt_deadline = time.time() + 120.0
        last_err: Any = None

        while time.time() < attempt_deadline:
            try:
                h, r0, rB, ids, proposer0, proposerB = await _pick_live_hr(dst=dst, peers=peers, timeout_s=20.0)

                # Re-check immediately before injecting to avoid racing the tick.
                st_chk = await http_get(dst.base_url, "/api/p2p/consensus_status", timeout_s=8.0)
                assert int(st_chk.get("status") or 0) == 200
                j_chk = st_chk.get("json") or {}
                if (
                    int(j_chk.get("height") or 0) != h
                    or int(j_chk.get("round") or 0) != r0
                    or bool(j_chk.get("have_proposal") is True)
                    or int(j_chk.get("finalized_height") or 0) >= h
                ):
                    await asyncio.sleep(0.05)
                    continue

                senderA = peer_by_val[proposer0]
                senderB = peer_by_val[proposerB]

                bidA = _canon_block_id(h, r0, proposer0)
                bidB = _canon_block_id(h, rB, proposerB)

                # 1) Proposal A at (h,r0)
                pA = {"height": h, "round": r0, "proposer": proposer0, "block_id": bidA, "block": {}, "ts_ms": _now_ms()}
                rr = await _post_signed(dst.base_url, "/api/p2p/proposal", src=senderA, msg_type="PROPOSAL", chain_id=dst.chain_id, payload_wo_sig=pA)
                if int(rr.get("status") or 0) != 200:
                    raise RuntimeError(f"proposal A rejected: {rr}")

                # 2) PREVOTE quorum for A (3-of-4) - send fast
                async def _send_prev(p) -> None:
                    vA = {"height": h, "round": r0, "voter": p.val_id, "vote_type": "PREVOTE", "block_id": bidA, "ts_ms": _now_ms()}
                    rrv = await _post_signed(dst.base_url, "/api/p2p/vote", src=p, msg_type="VOTE", chain_id=dst.chain_id, payload_wo_sig=vA)
                    if int(rrv.get("status") or 0) != 200:
                        raise RuntimeError(f"prevote A send failed from {p.val_id}: {rrv}")

                await asyncio.gather(*[_send_prev(p) for p in peers])

                # Observe lock(A) (or QC referencing A) quickly before the engine runs away.
                def _saw_lockA(j: Dict[str, Any]) -> bool:
                    lock = j.get("lock") or {}
                    if int(lock.get("height") or 0) == h and str(lock.get("block_id") or "") == bidA:
                        return True
                    qc = j.get("last_qc") or {}
                    return int(qc.get("height") or -1) == h and str(qc.get("block_id") or "") == bidA

                await _wait_for_observation(dst=dst, pred=_saw_lockA, timeout_s=8.0, poll_s=0.05)

                # 3) Higher-round proposal B at same height
                pB = {"height": h, "round": rB, "proposer": proposerB, "block_id": bidB, "block": {}, "ts_ms": _now_ms()}
                rr = await _post_signed(dst.base_url, "/api/p2p/proposal", src=senderB, msg_type="PROPOSAL", chain_id=dst.chain_id, payload_wo_sig=pB)
                if int(rr.get("status") or 0) != 200:
                    raise RuntimeError(f"proposal B rejected: {rr}")

                # 4) PREVOTE quorum for B -> expect relock(B)
                async def _send_prevB(p) -> None:
                    vB = {"height": h, "round": rB, "voter": p.val_id, "vote_type": "PREVOTE", "block_id": bidB, "ts_ms": _now_ms()}
                    rrv = await _post_signed(dst.base_url, "/api/p2p/vote", src=p, msg_type="VOTE", chain_id=dst.chain_id, payload_wo_sig=vB)
                    if int(rrv.get("status") or 0) != 200:
                        raise RuntimeError(f"prevote B send failed from {p.val_id}: {rrv}")

                await asyncio.gather(*[_send_prevB(p) for p in peers])

                def _saw_lockB(j: Dict[str, Any]) -> bool:
                    lock = j.get("lock") or {}
                    if (
                        int(lock.get("height") or 0) == h
                        and int(lock.get("round") or -1) == rB
                        and str(lock.get("block_id") or "") == bidB
                    ):
                        return True
                    qc = j.get("last_qc") or {}
                    return int(qc.get("height") or -1) == h and str(qc.get("block_id") or "") == bidB

                await _wait_for_observation(dst=dst, pred=_saw_lockB, timeout_s=10.0, poll_s=0.05)
                return

            except Exception as e:
                last_err = e
                await asyncio.sleep(0.10)
                continue

        raise AssertionError(f"lock/relock gate flaked repeatedly; last_err={last_err!r}")

    finally:
        await stop_nodes(nodes)