from __future__ import annotations

import time
from typing import Any, Dict

import pytest
pytestmark = [pytest.mark.integration, pytest.mark.glyphchain]

from backend.tests.helpers import start_n_nodes, stop_nodes, http_post
from backend.modules.p2p.crypto_ed25519 import canonical_p2p_sign_bytes, sign_ed25519


def _now_ms() -> float:
    return float(time.time() * 1000.0)


def _import_proposal_model():
    for mod, name in (
        ("backend.modules.consensus.types", "Proposal"),
        ("backend.modules.consensus.consensus_types", "Proposal"),
        ("backend.modules.consensus.models", "Proposal"),
        ("backend.modules.consensus.engine", "Proposal"),
    ):
        try:
            m = __import__(mod, fromlist=[name])
            return getattr(m, name)
        except Exception:
            continue
    raise RuntimeError("could not import Proposal model (update import paths in this test)")


def _mk_min_proposal_payload(Proposal, *, height: int, round: int, proposer: str, block_id: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    fields = getattr(Proposal, "model_fields", None)
    if not isinstance(fields, dict) or not fields:
        raise RuntimeError("Proposal model_fields not found (expected pydantic v2 model)")

    # fill only required fields with safe defaults
    for name, field in fields.items():
        try:
            required = bool(field.is_required())
        except Exception:
            required = getattr(field, "default", None) is None and getattr(field, "default_factory", None) is None
        if not required:
            continue

        k = str(name)
        if k == "height":
            payload[k] = int(height)
        elif k == "round":
            payload[k] = int(round)
        elif k in ("proposer", "proposer_val_id", "val_id"):
            payload[k] = str(proposer)
        elif k == "block_id":
            payload[k] = str(block_id)
        elif k == "block":
            payload[k] = {}  # important: some models reject None
        elif k in ("ts_ms", "timestamp_ms"):
            payload[k] = _now_ms()
        else:
            # best-effort generic default
            ann = getattr(field, "annotation", None)
            if ann is int:
                payload[k] = 0
            elif ann is float:
                payload[k] = _now_ms()
            elif ann is bool:
                payload[k] = True
            elif ann is str:
                payload[k] = "x"
            else:
                payload[k] = None

    # ensure parseable
    Proposal(**payload)
    return payload


@pytest.mark.integration
@pytest.mark.asyncio
async def test_consensus_pr6_noncanonical_proposal_reject_gate() -> None:
    nodes = await start_n_nodes(3, base_port=18080, chain_id="glyphchain-dev")
    try:
        Proposal = _import_proposal_model()

        src = nodes[0]  # val1 (leader for h=1,r=0)
        dst = nodes[1]

        h, r = 1, 0
        canonical_bid = f"h{h}-r{r}-P{src.val_id}"

        # 1) canonical proposal must be accepted
        payload_ok = _mk_min_proposal_payload(
            Proposal, height=h, round=r, proposer=src.val_id, block_id=canonical_bid
        )
        sig_ok = sign_ed25519(
            src.p2p_privkey_hex,
            canonical_p2p_sign_bytes(msg_type="PROPOSAL", chain_id=src.chain_id, payload=payload_ok),
        )
        payload_ok = dict(payload_ok)
        payload_ok["sig_hex"] = sig_ok

        env_ok = {
            "type": "PROPOSAL",
            "from_node_id": src.node_id,
            "from_val_id": src.val_id,
            "chain_id": src.chain_id,
            "ts_ms": _now_ms(),
            "payload": payload_ok,
            "hops": 0,
        }

        r1 = await http_post(dst.base_url, "/api/p2p/proposal", env_ok, timeout_s=6.0)
        assert int(r1.get("status") or 0) == 200, f"expected 200 for canonical proposal, got: {r1}"

        # 2) non-canonical proposal (same h/r/proposer but different block_id) must be rejected
        bad_bid = canonical_bid + "-evil"
        payload_bad = _mk_min_proposal_payload(
            Proposal, height=h, round=r, proposer=src.val_id, block_id=bad_bid
        )
        sig_bad = sign_ed25519(
            src.p2p_privkey_hex,
            canonical_p2p_sign_bytes(msg_type="PROPOSAL", chain_id=src.chain_id, payload=payload_bad),
        )
        payload_bad = dict(payload_bad)
        payload_bad["sig_hex"] = sig_bad

        env_bad = dict(env_ok)
        env_bad["payload"] = payload_bad

        r2 = await http_post(dst.base_url, "/api/p2p/proposal", env_bad, timeout_s=6.0)
        assert int(r2.get("status") or 0) in (400, 403), f"expected reject, got: {r2}"

    finally:
        await stop_nodes(nodes)