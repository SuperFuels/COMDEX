from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional
import re

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.glyphchain]

from backend.tests.helpers import start_n_nodes, stop_nodes, http_get, http_post
from backend.modules.p2p.crypto_ed25519 import canonical_p2p_sign_bytes, sign_ed25519

_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")


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


async def _wait_status_ready(node, timeout_s: float = 180.0) -> None:
    """
    Gate on ONE node responding. If this times out, the node is wedged (likely lock deadlock),
    not a test flake.
    """
    deadline = time.time() + float(timeout_s)
    last_err: Optional[str] = None

    while time.time() < deadline:
        try:
            r = await http_get(node.base_url, "/api/p2p/consensus_status", timeout_s=20.0)
            if int(r.get("status") or 0) == 200:
                return
            last_err = f"status={r.get('status')} body={r.get('text')}"
        except Exception as e:
            last_err = repr(e)

        await asyncio.sleep(0.25)

    raise AssertionError(f"node never became ready (node_id={node.node_id}) last_err={last_err}")


async def _post_one_with_retry(
    *,
    src,
    dst,
    path: str,
    msg_type: str,
    payload: Dict[str, Any],
    expect_status: int = 200,
    expect_accepted: Optional[bool] = None,
) -> None:
    # Ensure the destination is serving HTTP before we try to push envelopes into it.
    await _wait_status_ready(dst, timeout_s=60.0)

    last: Any = None
    for i in range(10):
        try:
            rr = await http_post(
                dst.base_url,
                path,
                _mk_env(src=src, msg_type=msg_type, payload=payload),
                timeout_s=20.0,
            )
            last = rr

            st = int(rr.get("status") or 0)
            detail = str(rr.get("detail") or (rr.get("json") or {}).get("detail") or rr.get("text") or "")

            # HELLO not yet visible on dst -> retry (peer_store has no self-record; skip-self is required)
            if st == 403 and ("hello_ok" in detail or "peer" in detail.lower()):
                await asyncio.sleep(0.25)
                continue

            assert st == int(expect_status), rr

            if expect_accepted is not None:
                j = rr.get("json") or {}
                assert isinstance(j, dict), rr
                assert bool(j.get("accepted")) == bool(expect_accepted), rr

            return

        except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            last = repr(e)
            await asyncio.sleep(0.25 * (2 ** min(i, 4)))
            continue
        except Exception as e:
            last = repr(e)
            await asyncio.sleep(0.25 * (2 ** min(i, 4)))
            continue

    raise AssertionError(f"post failed after retries src={src.node_id} dst={dst.node_id} last={last}")


async def _post_to_many_skip_self(
    *,
    src,
    dsts,
    path: str,
    msg_type: str,
    payload: Dict[str, Any],
    expect_status: int = 200,
    expect_accepted: Optional[bool] = None,
) -> None:
    for dst in dsts:
        if dst.node_id == src.node_id:
            continue  # never post to self (no self peer_store record)
        await _post_one_with_retry(
            src=src,
            dst=dst,
            path=path,
            msg_type=msg_type,
            payload=payload,
            expect_status=expect_status,
            expect_accepted=expect_accepted,
        )


@pytest.mark.asyncio
async def test_consensus_pr6_two_competing_rounds_preferred_convergence_gate() -> None:
    nodes = await start_n_nodes(4, base_port=18180, chain_id="glyphchain-dev")
    try:
        # If this fails, fix the engine deadlock first (not the test).
        await _wait_status_ready(nodes[0], timeout_s=180.0)

        st0 = await _get_status(nodes[0])
        validators = list(st0.get("validators") or [])
        assert validators, f"no validators in status: {st0}"

        base_fh = int(st0.get("finalized_height") or 0)
        h = int(base_fh + 25)  # far enough ahead to avoid racing normal progress

        leader0 = _leader_for(validators, h, 0)
        leader1 = _leader_for(validators, h, 1)
        assert leader0 is not None and leader1 is not None

        blockA = _canon_block_id(h, 0, leader0)
        blockB = _canon_block_id(h, 1, leader1)

        gA = [nodes[0], nodes[1]]  # see (h,0) first
        gB = [nodes[2], nodes[3]]  # see (h,1) first

        # --- Step 1: split proposals (A to gA, B to gB) ---
        src_for_A = nodes[2]  # not in gA
        pA: Dict[str, Any] = {
            "height": h,
            "round": 0,
            "proposer": leader0,
            "block_id": blockA,
            "block": {},
            "ts_ms": _now_ms(),
        }
        pA["sig_hex"] = _sign_payload(src_for_A, msg_type="PROPOSAL", payload=pA)
        await _post_to_many_skip_self(src=src_for_A, dsts=gA, path="/api/p2p/proposal", msg_type="PROPOSAL", payload=pA)

        src_for_B = nodes[0]  # not in gB
        pB: Dict[str, Any] = {
            "height": h,
            "round": 1,
            "proposer": leader1,
            "block_id": blockB,
            "block": {},
            "ts_ms": _now_ms(),
        }
        pB["sig_hex"] = _sign_payload(src_for_B, msg_type="PROPOSAL", payload=pB)
        await _post_to_many_skip_self(src=src_for_B, dsts=gB, path="/api/p2p/proposal", msg_type="PROPOSAL", payload=pB)

        await asyncio.sleep(0.25)

        # --- Step 2: split prevotes but keep below quorum ---
        for voter_node in (nodes[0], nodes[1]):
            vA: Dict[str, Any] = {
                "height": h,
                "round": 0,
                "voter": voter_node.val_id,
                "vote_type": "PREVOTE",
                "block_id": blockA,
                "ts_ms": _now_ms(),
            }
            vA["sig_hex"] = _sign_payload(voter_node, msg_type="VOTE", payload=vA)
            await _post_to_many_skip_self(src=voter_node, dsts=gA, path="/api/p2p/vote", msg_type="VOTE", payload=vA)

        for voter_node in (nodes[2], nodes[3]):
            vB_part: Dict[str, Any] = {
                "height": h,
                "round": 1,
                "voter": voter_node.val_id,
                "vote_type": "PREVOTE",
                "block_id": blockB,
                "ts_ms": _now_ms(),
            }
            vB_part["sig_hex"] = _sign_payload(voter_node, msg_type="VOTE", payload=vB_part)
            await _post_to_many_skip_self(src=voter_node, dsts=gB, path="/api/p2p/vote", msg_type="VOTE", payload=vB_part)

        await asyncio.sleep(0.25)

        # --- Step 3: ensure gA learns round=1 (preference should become 1) ---
        for voter_node in (nodes[2], nodes[3]):
            vB_hint: Dict[str, Any] = {
                "height": h,
                "round": 1,
                "voter": voter_node.val_id,
                "vote_type": "PREVOTE",
                "block_id": blockB,
                "ts_ms": _now_ms(),
            }
            vB_hint["sig_hex"] = _sign_payload(voter_node, msg_type="VOTE", payload=vB_hint)
            await _post_to_many_skip_self(src=voter_node, dsts=gA, path="/api/p2p/vote", msg_type="VOTE", payload=vB_hint)

        # --- Step 4 (canary): flood full r=0 prevote set everywhere; must be accepted-but-ignored ---
        for voter_node in nodes:
            vA_stale: Dict[str, Any] = {
                "height": h,
                "round": 0,
                "voter": voter_node.val_id,
                "vote_type": "PREVOTE",
                "block_id": blockA,
                "ts_ms": _now_ms(),
            }
            vA_stale["sig_hex"] = _sign_payload(voter_node, msg_type="VOTE", payload=vA_stale)
            await _post_to_many_skip_self(
                src=voter_node,
                dsts=nodes,
                path="/api/p2p/vote",
                msg_type="VOTE",
                payload=vA_stale,
                expect_status=200,
                expect_accepted=False,
            )

        # --- Step 5: finalize deterministically on round=1 (B) ---
        for voter_node in nodes:
            vB: Dict[str, Any] = {
                "height": h,
                "round": 1,
                "voter": voter_node.val_id,
                "vote_type": "PREVOTE",
                "block_id": blockB,
                "ts_ms": _now_ms(),
            }
            vB["sig_hex"] = _sign_payload(voter_node, msg_type="VOTE", payload=vB)
            await _post_to_many_skip_self(src=voter_node, dsts=nodes, path="/api/p2p/vote", msg_type="VOTE", payload=vB)

        for voter_node in nodes:
            cB: Dict[str, Any] = {
                "height": h,
                "round": 1,
                "voter": voter_node.val_id,
                "vote_type": "PRECOMMIT",
                "block_id": blockB,
                "ts_ms": _now_ms(),
            }
            cB["sig_hex"] = _sign_payload(voter_node, msg_type="VOTE", payload=cB)
            await _post_to_many_skip_self(src=voter_node, dsts=nodes, path="/api/p2p/vote", msg_type="VOTE", payload=cB)

        # --- Assert: all nodes finalized height h on round=1 blockB ---
        deadline = time.time() + 25.0
        while time.time() < deadline:
            hs = [int((await _get_status(n)).get("finalized_height") or 0) for n in nodes]
            if min(hs) >= h:
                break
            await asyncio.sleep(0.25)

        for n in nodes:
            st = await _get_status(n)
            assert int(st.get("finalized_height") or 0) >= h, f"node did not finalize h={h}: {st}"
            last_qc = st.get("last_qc") or {}
            assert isinstance(last_qc, dict) and last_qc, f"missing last_qc: {st}"
            assert int(last_qc.get("height") or 0) == h, f"wrong qc height: {st}"
            assert int(last_qc.get("round") or -1) == 1, f"expected qc round=1: {st}"
            assert str(last_qc.get("block_id") or "") == blockB, f"expected finalize on B: {st}"

    finally:
        await stop_nodes(nodes)