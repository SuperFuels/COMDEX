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


def _proposal_fp_from_payload(payload: Dict[str, Any]) -> str:
    # Prefer using the engine's real fingerprint function.
    try:
        from backend.modules.consensus.types import Proposal  # type: ignore
        from backend.modules.consensus.engine import _proposal_fingerprint  # type: ignore

        p = Proposal(**payload)  # includes sig_hex; msg_id excluded by route anyway
        return str(_proposal_fingerprint(p))
    except Exception:
        # fallback: stable-ish string; test may be less meaningful if this triggers
        return str(payload.get("block_id") or "")


async def _wait_for_proposal_fp(node, *, want_h: int, want_r: int, timeout_s: float = 6.0) -> Optional[str]:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        st = await _get_status(node)
        h = int(st.get("height") or 0)
        r = int(st.get("round") or 0)
        fp = st.get("proposal_fp")
        if h == int(want_h) and r == int(want_r) and isinstance(fp, str) and fp:
            return fp
        # no sleep storms; keep it light
        await asyncio.sleep(0.05)
    return None


@pytest.mark.asyncio
async def test_consensus_pr6_fork_choice_fp_gate(monkeypatch) -> None:
    # Slow things down a bit so status likely stays on (h,r) while we assert.
    monkeypatch.setenv("CONSENSUS_TICK_MS", "250")
    monkeypatch.setenv("CONSENSUS_ROUND_TIMEOUT_MS", "8000")

    nodes = await start_n_nodes(4, base_port=18470, chain_id="glyphchain-dev")
    try:
        st0 = await _get_status(nodes[0])
        validators = list(st0.get("validators") or [])
        assert validators, st0

        fh = int(st0.get("finalized_height") or 0)
        h = int(fh + 1)
        r = 0
        leader = _leader_for(validators, h, r) or validators[0]
        block_id = _canon_block_id(h, r, leader)

        sender = nodes[1]
        dst_a = nodes[2]
        dst_b = nodes[3]

        # Two competing proposals at same (h,r), same canonical fields, different block bodies.
        base_ts = _now_ms()

        pA: Dict[str, Any] = {
            "height": h,
            "round": r,
            "proposer": leader,
            "block_id": block_id,
            "block": {"variant": "A", "x": 1},
            "ts_ms": base_ts,
        }
        pA["sig_hex"] = _sign_payload(sender, msg_type="PROPOSAL", payload=pA)
        pA["msg_id"] = f"forkA:{int(base_ts)}"

        pB: Dict[str, Any] = {
            "height": h,
            "round": r,
            "proposer": leader,
            "block_id": block_id,
            "block": {"variant": "B", "x": 2},
            "ts_ms": base_ts,  # keep same; fingerprint should still differ via block body
        }
        pB["sig_hex"] = _sign_payload(sender, msg_type="PROPOSAL", payload=pB)
        pB["msg_id"] = f"forkB:{int(base_ts)}"

        fpA = _proposal_fp_from_payload({k: v for k, v in pA.items() if k != "msg_id"})
        fpB = _proposal_fp_from_payload({k: v for k, v in pB.items() if k != "msg_id"})
        # If fingerprint ended up equal (unexpected), force a deterministic difference via ts_ms.
        if fpA == fpB:
            pB["ts_ms"] = base_ts + 1.0
            pB["sig_hex"] = _sign_payload(sender, msg_type="PROPOSAL", payload={k: v for k, v in pB.items() if k != "msg_id"})
            fpB = _proposal_fp_from_payload({k: v for k, v in pB.items() if k != "msg_id"})

        expected = min(str(fpA), str(fpB))

        envA = {
            "type": "PROPOSAL",
            "from_node_id": sender.node_id,
            "from_val_id": sender.val_id,
            "chain_id": sender.chain_id,
            "ts_ms": _now_ms(),
            "payload": pA,
            "hops": 0,
        }
        envB = {
            "type": "PROPOSAL",
            "from_node_id": sender.node_id,
            "from_val_id": sender.val_id,
            "chain_id": sender.chain_id,
            "ts_ms": _now_ms(),
            "payload": pB,
            "hops": 0,
        }

        # Send opposite orders.
        r1 = await http_post(dst_a.base_url, "/api/p2p/proposal", envA, timeout_s=10.0)
        r2 = await http_post(dst_a.base_url, "/api/p2p/proposal", envB, timeout_s=10.0)
        r3 = await http_post(dst_b.base_url, "/api/p2p/proposal", envB, timeout_s=10.0)
        r4 = await http_post(dst_b.base_url, "/api/p2p/proposal", envA, timeout_s=10.0)

        for rr in (r1, r2, r3, r4):
            stc = int(rr.get("status") or 0)
            assert stc in (200, 400, 403), rr  # never 500

        # Pull proposal_fp from both nodes; they must converge to the same lexicographically-smallest fp.
        fp_a = await _wait_for_proposal_fp(dst_a, want_h=h, want_r=r, timeout_s=6.0)
        fp_b = await _wait_for_proposal_fp(dst_b, want_h=h, want_r=r, timeout_s=6.0)

        assert isinstance(fp_a, str) and fp_a, (await _get_status(dst_a))
        assert isinstance(fp_b, str) and fp_b, (await _get_status(dst_b))

        assert fp_a == fp_b, (fp_a, fp_b, await _get_status(dst_a), await _get_status(dst_b))
        assert fp_a == expected, (expected, fpA, fpB, fp_a)

    finally:
        await stop_nodes(nodes)