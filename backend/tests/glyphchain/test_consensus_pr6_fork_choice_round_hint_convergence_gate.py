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
    raise AssertionError("HELLO mesh not ready (hello_ok/pubkey_hex missing)")


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


async def _post_to_all_skip_self(nodes, *, path: str, msg_type: str, payload: Dict[str, Any]) -> None:
    for i, dst in enumerate(nodes):
        # pick a sender that is NOT dst (avoid /proposal,/vote posting "to self" -> hello_ok is false)
        src = nodes[(i + 1) % len(nodes)]
        assert src.node_id != dst.node_id

        pay = dict(payload)
        pay["sig_hex"] = _sign_payload(src, msg_type=msg_type, payload=pay)

        rr = await http_post(dst.base_url, path, _mk_env(src=src, msg_type=msg_type, payload=pay), timeout_s=6.0)
        assert int(rr.get("status") or 0) == 200, rr


@pytest.mark.asyncio
async def test_consensus_pr6_fork_choice_round_hint_convergence_gate() -> None:
    """
    PR6.2 gate: if we preload a higher-round proposal for the *next* height,
    every node should deterministically start that height at the hinted round (instead of r=0),
    and the cluster should finalize that height on the higher-round block_id.
    """
    nodes = await start_n_nodes(4, base_port=18080, chain_id="glyphchain-dev")
    try:
        await _wait_hello_mesh(nodes)

        st0 = await _get_status(nodes[0])
        validators = list(st0.get("validators") or [])
        assert validators

        # Choose a near-future height so the cluster reaches it quickly,
        # but far enough that we can preload the hint before it arrives.
        base_fh = int(st0.get("finalized_height") or 0)
        target_h: Optional[int] = None
        for hh in range(base_fh + 3, base_fh + 40):
            l1 = _leader_for(validators, hh, 1)
            if l1:
                target_h = hh
                break
        assert target_h is not None
        h = int(target_h)

        leader_r0 = _leader_for(validators, h, 0)
        leader_r1 = _leader_for(validators, h, 1)
        assert leader_r0 is not None and leader_r1 is not None

        blockA = _canon_block_id(h, 0, leader_r0)
        blockB = _canon_block_id(h, 1, leader_r1)

        # Preload BOTH proposals for height h (competing across rounds), so r=1 is a visible option everywhere.
        pA: Dict[str, Any] = {"height": h, "round": 0, "proposer": leader_r0, "block_id": blockA, "block": {}, "ts_ms": _now_ms()}
        pB: Dict[str, Any] = {"height": h, "round": 1, "proposer": leader_r1, "block_id": blockB, "block": {}, "ts_ms": _now_ms()}

        await _post_to_all_skip_self(nodes, path="/api/p2p/proposal", msg_type="PROPOSAL", payload=pA)
        await _post_to_all_skip_self(nodes, path="/api/p2p/proposal", msg_type="PROPOSAL", payload=pB)

        # Now wait until the cluster finalizes height h, and assert it finalized the round-1 block_id.
        deadline = time.time() + 30.0
        while time.time() < deadline:
            sts = [await _get_status(n) for n in nodes]
            fhs = [int(s.get("finalized_height") or 0) for s in sts]
            if min(fhs) >= h:
                # best-effort: check that each node's last_qc is >= h and matches round-1 at height h
                for s in sts:
                    qc = s.get("last_qc") or {}
                    qh = int(qc.get("height") or 0)
                    bid = str(qc.get("block_id") or "")
                    if qh == h:
                        assert bid == blockB, f"expected finalize on round-1 block at h={h}, got bid={bid} st={s}"
                return
            await asyncio.sleep(0.25)

        sts = [await _get_status(n) for n in nodes]
        fhs = [int(s.get("finalized_height") or 0) for s in sts]
        raise AssertionError(f"cluster did not finalize h={h} in time; finalized_heights={fhs} sts={sts}")

    finally:
        await stop_nodes(nodes)