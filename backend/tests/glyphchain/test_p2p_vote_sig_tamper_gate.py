# backend/tests/test_p2p_vote_sig_tamper_gate.py
from __future__ import annotations

import time
from typing import Any, Dict, Optional

import pytest
pytestmark = [pytest.mark.integration, pytest.mark.glyphchain]
from backend.tests.helpers import start_n_nodes, stop_nodes, http_post

from backend.modules.p2p.crypto_ed25519 import (
    canonical_p2p_sign_bytes,
    sign_ed25519,
)


def _now_ms() -> float:
    return float(time.time() * 1000.0)


def _import_vote_model():
    # Try a few common paths (keep this resilient to refactors)
    for mod, name in (
        ("backend.modules.consensus.types", "Vote"),
        ("backend.modules.consensus.consensus_types", "Vote"),
        ("backend.modules.consensus.models", "Vote"),
        ("backend.modules.consensus.engine", "Vote"),
    ):
        try:
            m = __import__(mod, fromlist=[name])
            return getattr(m, name)
        except Exception:
            continue
    raise RuntimeError("could not import Vote model (update import paths in this test)")


def _default_for_field(field) -> Any:
    """
    Pydantic v2 field object -> a safe default that passes common validators.
    """
    ann = getattr(field, "annotation", None)

    # Literal -> first allowed value
    try:
        from typing import get_origin, get_args, Literal  # py3.12

        if get_origin(ann) is Literal:
            args = list(get_args(ann) or [])
            if args:
                return args[0]
    except Exception:
        pass

    # Simple types
    if ann is int:
        return 1
    if ann is float:
        return _now_ms()
    if ann is bool:
        return True
    if ann is str:
        return "x"
    if ann is dict or ann is Dict:
        return {}
    if ann is list:
        return []

    # Optional/Union or unknown -> None is often accepted; else fallback "x"
    return None


def _mk_vote_payload(Vote, *, src_val_id: str) -> Dict[str, Any]:
    """
    Build a pydantic-valid Vote payload without needing consensus semantics.
    This gate is about signature verification, not vote correctness.
    """
    payload: Dict[str, Any] = {}

    fields = getattr(Vote, "model_fields", None)
    if not isinstance(fields, dict) or not fields:
        raise RuntimeError("Vote model_fields not found (expected pydantic v2 model)")

    for name, field in fields.items():
        # required?
        required = False
        try:
            required = bool(field.is_required())
        except Exception:
            # fallback heuristic
            required = getattr(field, "default", None) is None and getattr(field, "default_factory", None) is None

        if not required:
            continue

        key = str(name)

        # common consensus fields we can set “reasonably”
        if key in ("voter", "voter_val_id", "val_id", "from_val_id"):
            payload[key] = (src_val_id or "").strip() or "val1"
            continue
        if key == "height":
            payload[key] = 1
            continue
        if key == "round":
            payload[key] = 0
            continue
        if key in ("vote_type", "type"):
            payload[key] = "PREVOTE"
            continue
        if key in ("block_id", "proposal_id"):
            payload[key] = "h1-r0-Ptest"
            continue

        payload[key] = _default_for_field(field)

    # Validate locally to ensure the server will parse it as Vote(**payload)
    Vote(**payload)
    return payload


@pytest.mark.integration
@pytest.mark.asyncio
async def test_p2p_vote_sig_tamper_gate() -> None:
    nodes = await start_n_nodes(3, base_port=18080, chain_id="glyphchain-dev")
    try:
        Vote = _import_vote_model()

        src = nodes[0]  # signer identity (val1)
        dst = nodes[1]  # verifier node

        # Build a pydantic-valid vote payload
        payload = _mk_vote_payload(Vote, src_val_id=src.val_id)

        # Sign it with the node’s deterministic test privkey
        sig_msg = canonical_p2p_sign_bytes(msg_type="VOTE", chain_id=src.chain_id, payload=payload)
        sig_hex = sign_ed25519(src.p2p_privkey_hex, sig_msg)
        payload_signed = dict(payload)
        payload_signed["sig_hex"] = sig_hex

        # Send tampered payload with original sig -> MUST 403
        tampered = dict(payload_signed)
        if "round" in tampered and isinstance(tampered["round"], int):
            tampered["round"] = int(tampered["round"]) + 1
        elif "block_id" in tampered and isinstance(tampered["block_id"], str):
            tampered["block_id"] = tampered["block_id"] + "-tampered"
        else:
            # guaranteed to change sign-bytes while staying pydantic-valid for most models
            tampered["memo"] = "tampered"

        env = {
            "type": "VOTE",
            "from_node_id": src.node_id,
            "from_val_id": src.val_id,
            "chain_id": src.chain_id,
            "ts_ms": _now_ms(),
            "payload": tampered,
            "hops": 0,
        }

        r = await http_post(dst.base_url, "/api/p2p/vote", env, timeout_s=6.0)
        assert int(r.get("status") or 0) == 403, f"expected 403 on tampered sig, got: {r}"

    finally:
        await stop_nodes(nodes)