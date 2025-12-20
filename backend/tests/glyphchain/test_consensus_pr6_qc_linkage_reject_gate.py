# backend/tests/test_consensus_pr6_qc_linkage_reject_gate.py
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

import pytest
pytestmark = [pytest.mark.integration, pytest.mark.glyphchain]

from backend.tests.helpers import start_n_nodes, stop_nodes, http_get, http_post


def _now_ms() -> float:
    return float(time.time() * 1000.0)


def _status_tip(st: Dict[str, Any]) -> tuple[int, Optional[Dict[str, Any]]]:
    fh = int(st.get("finalized_height") or 0)
    last_qc = st.get("last_qc")
    return fh, (last_qc if isinstance(last_qc, dict) else None)


def _mk_env(*, src, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "SYNC_RESP",
        "from_node_id": src.node_id,
        "from_val_id": src.val_id,
        "chain_id": src.chain_id,
        "ts_ms": _now_ms(),
        "payload": payload,
        "hops": 0,
    }


@pytest.mark.integration
@pytest.mark.asyncio
async def test_consensus_pr6_qc_linkage_reject_gate() -> None:
    nodes = await start_n_nodes(3, base_port=18080, chain_id="glyphchain-dev")
    try:
        src = nodes[0]
        dst = nodes[1]

        st0 = await http_get(dst.base_url, "/api/p2p/consensus_status", timeout_s=6.0)
        assert int(st0.get("status") or 0) == 200, f"status fetch failed: {st0}"
        base_fh, _base_qc = _status_tip(st0.get("json") or {})

        async def _assert_reject_and_no_jump(peer_fh: int, bad_block_id: str) -> None:
            st1 = await http_get(dst.base_url, "/api/p2p/consensus_status", timeout_s=6.0)
            assert int(st1.get("status") or 0) == 200, f"status fetch failed: {st1}"
            fh1, qc1 = _status_tip(st1.get("json") or {})

            # invalid QC must not fast-forward us to the claimed peer_fh (which we set far ahead)
            assert fh1 != int(peer_fh), f"dst finalized_height jumped to invalid peer_fh={peer_fh}"

            # must not install the invalid qc as last_qc
            if qc1 is not None:
                if int(qc1.get("height") or 0) == int(peer_fh) and str(qc1.get("block_id") or "") == str(bad_block_id):
                    raise AssertionError(f"dst last_qc adopted invalid qc: {qc1}")

        # --- Case 1: last_qc.vote_type != PRECOMMIT
        peer_fh = base_fh + 50
        bad_block_id = f"h{peer_fh}-r0-Pbad"
        payload = {
            "finalized_height": peer_fh,
            "round": 0,
            "last_qc": {
                "height": peer_fh,
                "round": 0,
                "vote_type": "PREVOTE",
                "block_id": bad_block_id,
                "voters": [n.val_id for n in nodes],
                "ts_ms": _now_ms(),
            },
        }
        r = await http_post(dst.base_url, "/api/p2p/sync_resp", _mk_env(src=src, payload=payload), timeout_s=6.0)
        assert int(r.get("status") or 0) == 400, f"expected 400, got: {r}"
        await _assert_reject_and_no_jump(peer_fh, bad_block_id)

        # --- Case 2: qc.height != finalized_height
        peer_fh = base_fh + 60
        bad_block_id = f"h{peer_fh}-r0-Pbad2"
        payload = {
            "finalized_height": peer_fh,
            "round": 0,
            "last_qc": {
                "height": peer_fh - 1,
                "round": 0,
                "vote_type": "PRECOMMIT",
                "block_id": bad_block_id,
                "voters": [n.val_id for n in nodes],
                "ts_ms": _now_ms(),
            },
        }
        r = await http_post(dst.base_url, "/api/p2p/sync_resp", _mk_env(src=src, payload=payload), timeout_s=6.0)
        assert int(r.get("status") or 0) == 400, f"expected 400, got: {r}"
        await _assert_reject_and_no_jump(peer_fh, bad_block_id)

        # --- Case 3: voters don’t sum to quorum
        peer_fh = base_fh + 70
        bad_block_id = f"h{peer_fh}-r0-Pbad3"
        payload = {
            "finalized_height": peer_fh,
            "round": 0,
            "last_qc": {
                "height": peer_fh,
                "round": 0,
                "vote_type": "PRECOMMIT",
                "block_id": bad_block_id,
                "voters": [],
                "ts_ms": _now_ms(),
            },
        }
        r = await http_post(dst.base_url, "/api/p2p/sync_resp", _mk_env(src=src, payload=payload), timeout_s=6.0)
        assert int(r.get("status") or 0) == 400, f"expected 400, got: {r}"
        await _assert_reject_and_no_jump(peer_fh, bad_block_id)

        # --- Case 4: qc.round goes backwards vs local last_qc at SAME height
        deadline = time.time() + 20.0
        while True:
            st = await http_get(dst.base_url, "/api/p2p/consensus_status", timeout_s=6.0)
            assert int(st.get("status") or 0) == 200, f"status fetch failed: {st}"
            j = st.get("json") or {}
            cur_fh = int(j.get("finalized_height") or 0)
            cur_qc = j.get("last_qc")
            if cur_fh > 0 and isinstance(cur_qc, dict):
                break
            if time.time() > deadline:
                raise AssertionError(f"dst never produced last_qc: {j}")
            await asyncio.sleep(0.25)

        peer_fh = int(cur_fh)
        cur_round = int(cur_qc.get("round") or 0)
        cur_bid = str(cur_qc.get("block_id") or f"h{peer_fh}-bid")
        bad_round = cur_round - 1

        payload = {
            "finalized_height": peer_fh,
            "round": int(j.get("round") or 0),
            "last_qc": {
                "height": peer_fh,
                "round": bad_round,
                "vote_type": "PRECOMMIT",
                "block_id": cur_bid,
                "voters": [n.val_id for n in nodes],
                "ts_ms": _now_ms(),
            },
        }

        r = await http_post(dst.base_url, "/api/p2p/sync_resp", _mk_env(src=src, payload=payload), timeout_s=6.0)

        # If dst advanced height between snapshot and handler, it may treat this as "<= fh" and not error.
        code = int(r.get("status") or 0)
        if code == 200:
            jresp = r.get("json") or {}
            assert isinstance(jresp, dict) and jresp.get("ok") is True and jresp.get("applied") is False, f"expected applied:false, got: {r}"
        else:
            assert code == 400, f"expected 400 or 200(applied:false), got: {r}"

        st2 = await http_get(dst.base_url, "/api/p2p/consensus_status", timeout_s=6.0)
        assert int(st2.get("status") or 0) == 200
        j2 = st2.get("json") or {}
        fh2 = int(j2.get("finalized_height") or 0)
        qc2 = j2.get("last_qc")
        assert isinstance(qc2, dict)

        assert fh2 >= peer_fh
        assert not (int(qc2.get("height") or 0) == peer_fh and int(qc2.get("round") or 0) == bad_round), f"dst adopted regressing qc: {qc2}"
        assert int(qc2.get("height") or 0) == fh2

        # --- Case 5: qc conflicts at SAME height + SAME round (different block_id)
        st = await http_get(dst.base_url, "/api/p2p/consensus_status", timeout_s=6.0)
        assert int(st.get("status") or 0) == 200, f"status fetch failed: {st}"
        j = st.get("json") or {}
        cur_fh = int(j.get("finalized_height") or 0)
        cur_qc = j.get("last_qc")
        assert cur_fh > 0 and isinstance(cur_qc, dict), f"dst has no last_qc: {j}"

        peer_fh = int(cur_fh)
        cur_round = int(cur_qc.get("round") or 0)
        cur_bid = str(cur_qc.get("block_id") or f"h{peer_fh}-bid")
        bad_bid = cur_bid + "-conflict"

        payload = {
            "finalized_height": peer_fh,
            "round": int(j.get("round") or 0),
            "last_qc": {
                "height": peer_fh,
                "round": cur_round,
                "vote_type": "PRECOMMIT",
                "block_id": bad_bid,  # conflict
                "voters": [n.val_id for n in nodes],  # quorum
                "ts_ms": _now_ms(),
            },
        }

        r = await http_post(dst.base_url, "/api/p2p/sync_resp", _mk_env(src=src, payload=payload), timeout_s=6.0)

        code = int(r.get("status") or 0)
        if code == 200:
            jresp = r.get("json") or {}
            assert isinstance(jresp, dict) and jresp.get("ok") is True and jresp.get("applied") is False, f"expected applied:false, got: {r}"
        else:
            assert code == 400, f"expected 400 or 200(applied:false), got: {r}"

        st3 = await http_get(dst.base_url, "/api/p2p/consensus_status", timeout_s=6.0)
        assert int(st3.get("status") or 0) == 200
        j3 = st3.get("json") or {}
        fh3 = int(j3.get("finalized_height") or 0)
        qc3 = j3.get("last_qc")
        assert isinstance(qc3, dict)

        assert fh3 >= peer_fh
        assert not (
            int(qc3.get("height") or 0) == peer_fh
            and int(qc3.get("round") or 0) == cur_round
            and str(qc3.get("block_id") or "") == bad_bid
        ), f"dst adopted conflicting qc: {qc3}"

    finally:
        await stop_nodes(nodes)