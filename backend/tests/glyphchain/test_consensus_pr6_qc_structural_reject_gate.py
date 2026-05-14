# backend/tests/test_consensus_pr6_qc_structural_reject_gate.py
from __future__ import annotations

import time
from typing import Any, Dict, Optional, List

import pytest
pytestmark = [pytest.mark.integration, pytest.mark.glyphchain]

from backend.tests.helpers import start_n_nodes, stop_nodes, http_get, http_post
from backend.modules.p2p.crypto_ed25519 import canonical_p2p_sign_bytes, sign_ed25519


def _now_ms() -> float:
    return float(time.time() * 1000.0)


def _status_tip(st: Dict[str, Any]) -> tuple[int, Optional[Dict[str, Any]]]:
    fh = int(st.get("finalized_height") or 0)
    last_qc = st.get("last_qc")
    return fh, (last_qc if isinstance(last_qc, dict) else None)


def _mk_env(*, src, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "VOTE",
        "from_node_id": src.node_id,
        "from_val_id": src.val_id,
        "chain_id": src.chain_id,
        "ts_ms": _now_ms(),
        "payload": payload,
        "hops": 0,
    }


def _sign_vote_payload(*, chain_id: str, src, payload_wo_sig: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(payload_wo_sig)
    msg = canonical_p2p_sign_bytes(msg_type="VOTE", chain_id=chain_id, payload=payload)
    payload["sig_hex"] = sign_ed25519(src.p2p_privkey_hex, msg)
    return payload


@pytest.mark.integration
@pytest.mark.asyncio
async def test_consensus_pr6_qc_structural_reject_gate() -> None:
    # 4 nodes => quorum should be reachable by sending 3 votes (avoid needing dst self-vote via p2p).
    nodes = await start_n_nodes(4, base_port=18140, chain_id="glyphchain-dev")
    try:
        dst = nodes[0]
        senders = [nodes[1], nodes[2], nodes[3]]

        st0 = await http_get(dst.base_url, "/api/p2p/consensus_status", timeout_s=6.0)
        assert int(st0.get("status") or 0) == 200, f"status fetch failed: {st0}"
        base_fh, base_qc = _status_tip(st0.get("json") or {})

        # Attack target: try to "vote-finalize" a far-ahead height with a NON-canonical block_id.
        target_h = int(base_fh) + 50
        target_r = 0
        bad_block_id = f"h{target_h}-r{target_r}-Pnotleader"  # violates canonical h{h}-r{r}-P{leader}

        # Send PRECOMMIT votes from 3 validators to try to form a QC at (target_h, target_r).
        # Expectation: structural QC validation should prevent installing this QC / fast-forwarding.
        seen_400 = False

        for src in senders:
            payload_wo = {
                "height": target_h,
                "round": target_r,
                "voter": src.val_id,
                "vote_type": "PRECOMMIT",
                "block_id": bad_block_id,
                "ts_ms": _now_ms(),
            }
            payload = _sign_vote_payload(chain_id=dst.chain_id, src=src, payload_wo_sig=payload_wo)

            r = await http_post(dst.base_url, "/api/p2p/vote", _mk_env(src=src, payload=payload), timeout_s=6.0)
            code = int(r.get("status") or 0)

            # Depending on *when* your engine chooses to validate, the rejection can show up on the
            # quorum-forming vote (most likely). Earlier votes may still 200/accepted.
            if code == 400:
                seen_400 = True
            elif code == 200:
                j = r.get("json") or {}
                assert isinstance(j, dict) and j.get("ok") is True, f"expected ok:true on non-quorum votes: {r}"
            else:
                raise AssertionError(f"expected 200 or 400, got: {r}")

        # Regardless of whether we saw the 400 on an earlier/later vote,
        # the critical invariant: dst must NOT jump to target_h and must NOT adopt bad QC.
        st1 = await http_get(dst.base_url, "/api/p2p/consensus_status", timeout_s=6.0)
        assert int(st1.get("status") or 0) == 200, f"status fetch failed: {st1}"
        fh1, qc1 = _status_tip(st1.get("json") or {})

        assert int(fh1) != int(target_h), f"dst finalized_height jumped to poisoned qc height={target_h}"
        if qc1 is not None:
            if (
                int(qc1.get("height") or 0) == int(target_h)
                and int(qc1.get("round") or 0) == int(target_r)
                and str(qc1.get("block_id") or "") == str(bad_block_id)
            ):
                raise AssertionError(f"dst last_qc adopted poisoned qc: {qc1}")

        # Soft assertion: at least one request should 400 once quorum is reached.
        # If this ever flakes due to timing, the invariant above is still the real gate.
        assert seen_400 is True, "expected at least one 400 rejection once quorum would form a QC"

    finally:
        await stop_nodes(nodes)