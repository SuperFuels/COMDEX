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


async def _wait_hello_mesh(nodes, timeout_s: float = 20.0) -> None:
    """
    start_n_nodes() sends hello_full_mesh(), but HELLO propagation/visibility is async.
    This waits until every node sees every other node as hello_ok with pubkey_hex.
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        ok = True
        for dst in nodes:
            r = await http_get(dst.base_url, "/api/p2p/peers", timeout_s=6.0)
            if int(r.get("status") or 0) != 200:
                ok = False
                break

            j = r.get("json") or {}
            peers = j.get("peers") or []
            by_node = {p.get("node_id"): p for p in peers if isinstance(p, dict) and p.get("node_id")}

            for src in nodes:
                if src.node_id == dst.node_id:
                    continue
                rec = by_node.get(src.node_id)
                if not (
                    isinstance(rec, dict)
                    and bool(rec.get("hello_ok"))
                    and str(rec.get("pubkey_hex") or "").strip()
                ):
                    ok = False
                    break

            if not ok:
                break

        if ok:
            return

        await asyncio.sleep(0.2)

    raise AssertionError("HELLO mesh not ready (hello_ok/pubkey_hex missing) before consensus sends")


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
    assert priv, f"missing p2p privkey hex for node={getattr(node,'node_id',None)}"
    msg = canonical_p2p_sign_bytes(msg_type=msg_type, chain_id=node.chain_id, payload=payload)
    sig = sign_ed25519(priv, msg)
    assert isinstance(sig, str) and sig.strip(), f"sign_ed25519 returned empty/non-str: {sig!r}"
    sig = sig.strip().lower()
    assert sig and _HEX_RE.match(sig), f"sig not hex: {sig!r}"
    return sig


async def _get_status(node) -> Dict[str, Any]:
    r = await http_get(node.base_url, "/api/p2p/consensus_status", timeout_s=6.0)
    assert int(r.get("status") or 0) == 200, r
    j = r.get("json") or {}
    assert isinstance(j, dict)
    return j


@pytest.mark.asyncio
async def test_consensus_pr6_round_fast_forward_convergence_gate() -> None:
    nodes = await start_n_nodes(4, base_port=18080, chain_id="glyphchain-dev")
    try:
        # ✅ must happen before any /proposal or /vote posts
        await _wait_hello_mesh(nodes)

        st0 = await _get_status(nodes[0])
        validators = list(st0.get("validators") or [])
        assert validators

        base_fh = int(st0.get("finalized_height") or 0)

        # Pick a near-future height where leaders exist for r=0 and r=1.
        target_h: Optional[int] = None
        for hh in range(base_fh + 5, base_fh + 80):
            l0 = _leader_for(validators, hh, 0)
            l1 = _leader_for(validators, hh, 1)
            if l0 and l1:
                target_h = hh
                break
        assert target_h is not None
        h = int(target_h)

        leader_r1 = _leader_for(validators, h, 1)
        assert leader_r1 is not None
        blockB = _canon_block_id(h, 1, leader_r1)

        # Send round-1 PROPOSAL first to all *other* nodes (don’t send to self).
        # Use node[0] as the envelope identity; proposer field is canonical leader_r1.
        src = nodes[0]
        pB: Dict[str, Any] = {
            "height": h,
            "round": 1,
            "proposer": leader_r1,
            "block_id": blockB,
            "block": {},
            "ts_ms": _now_ms(),
        }
        pB["sig_hex"] = _sign_payload(src, msg_type="PROPOSAL", payload=pB)

        for dst in nodes:
            if dst.node_id == src.node_id:
                continue  # ✅ avoid self-post (self peer record isn’t hello_ok)
            rr = await http_post(
                dst.base_url,
                "/api/p2p/proposal",
                _mk_env(src=src, msg_type="PROPOSAL", payload=pB),
                timeout_s=6.0,
            )
            assert int(rr.get("status") or 0) == 200, rr

        # Create PREVOTE quorum for (h,1) across all nodes.
        # Each node should auto-PRECOMMIT; quorum PRECOMMIT finalizes.
        for voter_node in nodes:
            v: Dict[str, Any] = {
                "height": h,
                "round": 1,
                "voter": voter_node.val_id,
                "vote_type": "PREVOTE",
                "block_id": blockB,
                "ts_ms": _now_ms(),
            }
            v["sig_hex"] = _sign_payload(voter_node, msg_type="VOTE", payload=v)

            for dst in nodes:
                if dst.node_id == voter_node.node_id:
                    continue  # ✅ avoid self-post (self peer record isn’t hello_ok)
                rr = await http_post(
                    dst.base_url,
                    "/api/p2p/vote",
                    _mk_env(src=voter_node, msg_type="VOTE", payload=v),
                    timeout_s=6.0,
                )
                assert int(rr.get("status") or 0) == 200, rr

        # All nodes should finalize height h soon
        deadline = time.time() + 25.0
        while time.time() < deadline:
            hs = [int((await _get_status(n)).get("finalized_height") or 0) for n in nodes]
            if min(hs) >= h:
                return
            await asyncio.sleep(0.25)

        hs = [int((await _get_status(n)).get("finalized_height") or 0) for n in nodes]
        raise AssertionError(f"cluster did not converge/finalize h={h}; finalized_heights={hs}")

    finally:
        await stop_nodes(nodes)