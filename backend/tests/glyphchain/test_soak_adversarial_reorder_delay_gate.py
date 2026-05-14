from __future__ import annotations

import asyncio
import random
import time
from typing import Any, Dict, Optional
import re
import os

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
    r = await http_get(node.base_url, "/api/p2p/consensus_status", timeout_s=10.0)
    assert int(r.get("status") or 0) == 200, r
    j = r.get("json") or {}
    assert isinstance(j, dict)
    return j


def _env_f(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)) or default)
    except Exception:
        return float(default)


@pytest.mark.asyncio
async def test_soak_adversarial_reorder_delay_gate(monkeypatch) -> None:
    # keep queues small so we actually see drops
    monkeypatch.setenv("P2P_LANE_MAX_QUEUE_VOTE", "32")
    monkeypatch.setenv("P2P_LANE_MAX_INFLIGHT_VOTE", "1")
    monkeypatch.setenv("P2P_LANE_DUP_LRU_VOTE", "256")

    monkeypatch.setenv("P2P_LANE_MAX_QUEUE_PROPOSAL", "32")
    monkeypatch.setenv("P2P_LANE_MAX_INFLIGHT_PROPOSAL", "1")
    monkeypatch.setenv("P2P_LANE_DUP_LRU_PROPOSAL", "256")

    # avoid huge RL interference
    monkeypatch.setenv("P2P_RL_MSG_PER_SEC", "500")
    monkeypatch.setenv("P2P_RL_MSG_BURST", "1000")

    # NOTE: if your environment is slow to boot, export GLYPHCHAIN_TEST_NODE_READY_TIMEOUT_S=240
    nodes = await start_n_nodes(4, base_port=18380, chain_id="glyphchain-dev")
    try:
        st0 = await _get_status(nodes[0])
        validators = list(st0.get("validators") or [])
        assert validators, f"no validators: {st0}"

        # pick a live height near the working tip (within future window)
        base_fh = int(st0.get("finalized_height") or 0)
        h = int(base_fh + 1)
        r = 0
        leader = _leader_for(validators, h, r) or validators[0]
        block_id = _canon_block_id(h, r, leader)

        sender = nodes[1]  # signs envelopes
        dsts = [n for n in nodes if n.node_id != sender.node_id]

        # craft one canonical proposal + votes (then spam/reorder/dup)
        p: Dict[str, Any] = {
            "height": h,
            "round": r,
            "proposer": leader,
            "block_id": block_id,
            "block": {},
            "ts_ms": _now_ms(),
        }
        p["sig_hex"] = _sign_payload(sender, msg_type="PROPOSAL", payload=p)

        v_prev: Dict[str, Any] = {
            "height": h,
            "round": r,
            "voter": sender.val_id,
            "vote_type": "PREVOTE",
            "block_id": block_id,
            "ts_ms": _now_ms(),
        }
        v_prev["sig_hex"] = _sign_payload(sender, msg_type="VOTE", payload=v_prev)

        v_pc: Dict[str, Any] = {
            "height": h,
            "round": r,
            "voter": sender.val_id,
            "vote_type": "PRECOMMIT",
            "block_id": block_id,
            "ts_ms": _now_ms(),
        }
        v_pc["sig_hex"] = _sign_payload(sender, msg_type="VOTE", payload=v_pc)

        dur_s = _env_f("GLYPHCHAIN_SOAK_DURATION_S", 25.0)
        end = time.monotonic() + float(dur_s)

        # monotonic finalized heights observed per node
        last_fh: Dict[str, int] = {n.node_id: int((await _get_status(n)).get("finalized_height") or 0) for n in nodes}

        errs_5xx = 0

        while time.monotonic() < end:
            dst = random.choice(dsts)
            choice = random.random()

            # reorder/jitter/dup floods
            if choice < 0.35:
                rr = await http_post(
                    dst.base_url,
                    "/api/p2p/vote",
                    _mk_env(src=sender, msg_type="VOTE", payload=v_prev),
                    timeout_s=10.0,
                )
            elif choice < 0.70:
                rr = await http_post(
                    dst.base_url,
                    "/api/p2p/proposal",
                    _mk_env(src=sender, msg_type="PROPOSAL", payload=p),
                    timeout_s=10.0,
                )
            else:
                rr = await http_post(
                    dst.base_url,
                    "/api/p2p/vote",
                    _mk_env(src=sender, msg_type="VOTE", payload=v_pc),
                    timeout_s=10.0,
                )

            if int(rr.get("status") or 0) >= 500:
                errs_5xx += 1

            # occasional SYNC/STATUS bursts (request-like) + BLOCK_REQ (may 404; must not 5xx)
            if random.random() < 0.10:
                env = _mk_env(src=sender, msg_type="STATUS", payload={"ts_ms": _now_ms()})
                r2 = await http_post(dst.base_url, "/api/p2p/status", env, timeout_s=10.0)
                if int(r2.get("status") or 0) >= 500:
                    errs_5xx += 1

            if random.random() < 0.10:
                env = _mk_env(src=sender, msg_type="SYNC_REQ", payload={"ts_ms": _now_ms()})
                r2 = await http_post(dst.base_url, "/api/p2p/sync_req", env, timeout_s=10.0)
                if int(r2.get("status") or 0) >= 500:
                    errs_5xx += 1

            if random.random() < 0.10:
                env = _mk_env(
                    src=sender,
                    msg_type="BLOCK_REQ",
                    payload={"height": max(1, base_fh), "want": "header"},
                )
                r2 = await http_post(dst.base_url, "/api/p2p/block_req", env, timeout_s=10.0)
                if int(r2.get("status") or 0) >= 500:
                    errs_5xx += 1

            # monotonic finalized_height on all nodes
            for n in nodes:
                st = await _get_status(n)
                fh = int(st.get("finalized_height") or 0)
                assert fh >= last_fh[n.node_id], (
                    f"finalized_height regressed on {n.node_id}: {last_fh[n.node_id]} -> {fh}"
                )
                last_fh[n.node_id] = fh

            await asyncio.sleep(random.uniform(0.0, 0.03))

        assert errs_5xx == 0, f"saw {errs_5xx} HTTP 5xx responses during soak"

        # must have drops in ingress (dup/full) somewhere
        drops = 0
        for n in nodes:
            st = await _get_status(n)
            ing = (st.get("p2p_ingress") or {}).get("lanes") if isinstance(st.get("p2p_ingress"), dict) else None
            if isinstance(ing, dict):
                for lane in ing.values():
                    c = (lane or {}).get("counters") or {}
                    drops += int(c.get("dropped_dup") or 0) + int(c.get("dropped_full") or 0)

        assert drops > 0, "expected ingress drops > 0 (dup/full) during soak"

    finally:
        await stop_nodes(nodes)