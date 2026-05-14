from __future__ import annotations

import asyncio
import re
import time
from typing import Any, Dict, Optional

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


def _p2p_priv_hex(n) -> str:
    return (
        (getattr(n, "p2p_privkey_hex", None) or "")
        or (getattr(n, "privkey_hex", None) or "")
        or (getattr(n, "priv_key_hex", None) or "")
    ).strip()


def _sign_payload(node, *, msg_type: str, payload: Dict[str, Any]) -> str:
    priv = _p2p_priv_hex(node)
    assert priv, "missing p2p privkey hex"
    msg = canonical_p2p_sign_bytes(msg_type=msg_type, chain_id=node.chain_id, payload=payload)
    sig = sign_ed25519(priv, msg)
    sig = str(sig or "").strip().lower()
    assert sig and _HEX_RE.match(sig), f"bad sig_hex: {sig!r}"
    return sig


async def _get_status(node) -> Dict[str, Any]:
    r = await http_get(node.base_url, "/api/p2p/consensus_status", timeout_s=10.0)
    assert int(r.get("status") or 0) == 200, r
    j = r.get("json") or {}
    assert isinstance(j, dict)
    return j


async def _wait_for_fh_at_least(node, want: int, *, timeout_s: float = 40.0) -> Dict[str, Any]:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        st = await _get_status(node)
        fh = int(st.get("finalized_height") or 0)
        if fh >= want:
            return st
        await asyncio.sleep(0.25)
    raise AssertionError(f"timeout waiting for finalized_height >= {want}")


@pytest.mark.asyncio
async def test_consensus_pr6_vote_past_height_ignore_gate() -> None:
    nodes = await start_n_nodes(3, base_port=18440, chain_id="glyphchain-dev")
    try:
        target = nodes[0]
        sender = nodes[1]

        st0 = await _wait_for_fh_at_least(target, 1, timeout_s=60.0)
        validators = list(st0.get("validators") or [])
        assert validators, st0

        fh0 = int(st0.get("finalized_height") or 0)
        last_qc0 = st0.get("last_qc") or {}

        # pick a past height (already-finalized). if fh0==1, use h=1.
        h = max(1, fh0)
        r = 0
        leader = _leader_for(validators, h, r) or validators[0]
        block_id = _canon_block_id(h, r, leader)

        v: Dict[str, Any] = {
            "height": int(h),
            "round": int(r),
            "voter": str(sender.val_id),
            "vote_type": "PREVOTE",
            "block_id": str(block_id),
            "ts_ms": _now_ms(),
        }
        v["sig_hex"] = _sign_payload(sender, msg_type="VOTE", payload=v)

        env = {
            "type": "VOTE",
            "from_node_id": sender.node_id,
            "from_val_id": sender.val_id,
            "chain_id": sender.chain_id,
            "ts_ms": _now_ms(),
            "payload": v,
            "hops": 0,
        }

        rr = await http_post(target.base_url, "/api/p2p/vote", env, timeout_s=10.0)
        stc = int(rr.get("status") or 0)
        assert stc in (200, 400, 403), rr  # never 500

        st1 = await _get_status(target)
        fh1 = int(st1.get("finalized_height") or 0)
        last_qc1 = st1.get("last_qc") or {}

        # past-height vote must not change tip
        assert fh1 == fh0, (st0, st1)
        # last_qc must not regress
        def _k(qc: Any) -> tuple[int, int]:
            if not isinstance(qc, dict):
                return (0, 0)
            return (int(qc.get("height") or 0), int(qc.get("round") or 0))

        assert _k(last_qc1) >= _k(last_qc0), (st0, st1)

    finally:
        await stop_nodes(nodes)