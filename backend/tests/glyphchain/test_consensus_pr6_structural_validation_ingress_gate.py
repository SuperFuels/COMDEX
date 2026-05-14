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

async def _status(node) -> Dict[str, Any]:
    r = await http_get(node.base_url, "/api/p2p/consensus_status", timeout_s=10.0)
    assert int(r.get("status") or 0) == 200, r
    j = r.get("json") or {}
    assert isinstance(j, dict)
    return j

async def _wait_fh(node, *, min_fh: int, timeout_s: float = 30.0) -> Dict[str, Any]:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        st = await _status(node)
        if int(st.get("finalized_height") or 0) >= int(min_fh):
            return st
        await asyncio.sleep(0.25)
    return await _status(node)

@pytest.mark.asyncio
async def test_consensus_pr6_structural_validation_ingress_gate() -> None:
    nodes = await start_n_nodes(3, base_port=18460, chain_id="glyphchain-dev")
    try:
        target = nodes[0]
        sender = nodes[1]

        st0 = await _wait_fh(target, min_fh=2, timeout_s=35.0)
        fh0 = int(st0.get("finalized_height") or 0)
        last0 = st0.get("last_qc")

        # --- malformed vote payload (missing/invalid fields) ---
        bad_vote: Dict[str, Any] = {
            # "height": missing on purpose
            "round": "nope",
            "vote_type": "GARBAGE",
            "block_id": "",
            "voter": "",
            "ts_ms": _now_ms(),
        }
        bad_vote["sig_hex"] = _sign_payload(sender, msg_type="VOTE", payload=bad_vote)

        rr = await http_post(
            target.base_url,
            "/api/p2p/vote",
            _mk_env(src=sender, msg_type="VOTE", payload=bad_vote),
            timeout_s=10.0,
        )
        assert int(rr.get("status") or 0) in (200, 400, 403), rr
        assert int(rr.get("status") or 0) < 500, rr

        st1 = await _status(target)
        assert int(st1.get("finalized_height") or 0) >= fh0, "finalized_height regressed after bad vote"
        assert st1.get("last_qc") == last0, "last_qc changed after bad vote"

        # --- malformed sync_resp QC dict (bad types / missing structure) ---
        bad_sync_payload: Dict[str, Any] = {
            "finalized_height": fh0,  # keep plausible
            "last_qc": {
                "height": "x",  # invalid
                "round": 0,
                "vote_type": "PRECOMMIT",
                "block_id": "h1-r0-Pval1",
                "voters": "not-a-list",  # invalid
                "ts_ms": _now_ms(),
            },
            "round": 0,
            "ts_ms": _now_ms(),
        }
        bad_sync_payload["sig_hex"] = _sign_payload(sender, msg_type="SYNC_RESP", payload=bad_sync_payload)

        rr2 = await http_post(
            target.base_url,
            "/api/p2p/sync_resp",
            _mk_env(src=sender, msg_type="SYNC_RESP", payload=bad_sync_payload),
            timeout_s=10.0,
        )
        assert int(rr2.get("status") or 0) in (200, 400, 403), rr2
        assert int(rr2.get("status") or 0) < 500, rr2

        st2 = await _status(target)
        assert int(st2.get("finalized_height") or 0) >= fh0, "finalized_height regressed after bad sync_resp"
        assert st2.get("last_qc") == last0, "last_qc changed after bad sync_resp"

    finally:
        await stop_nodes(nodes)