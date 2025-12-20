# backend/tests/test_p2p_proposal_sig_tamper_gate.py
from __future__ import annotations

import time
from typing import Any, Dict

import pytest
pytestmark = [pytest.mark.integration, pytest.mark.glyphchain]
from pydantic import BaseModel

from backend.tests.helpers import start_n_nodes, stop_nodes, http_post

from backend.modules.p2p.crypto_ed25519 import (
    canonical_p2p_sign_bytes,
    sign_ed25519,
)


def _now_ms() -> float:
    return float(time.time() * 1000.0)


def _import_proposal_model():
    # Try a few common paths (keep this resilient to refactors)
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

    return None


def _mk_pydantic_payload(Model, overrides: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a pydantic-valid payload recursively for BaseModel fields.
    This keeps the gate about signature verification, not consensus semantics.
    """
    payload: Dict[str, Any] = {}
    fields = getattr(Model, "model_fields", None)
    if not isinstance(fields, dict) or not fields:
        raise RuntimeError(f"{getattr(Model, '__name__', 'Model')} model_fields not found (expected pydantic v2 model)")

    for name, field in fields.items():
        key = str(name)

        # if caller provided override, use it (even if optional)
        if key in overrides:
            payload[key] = overrides[key]
            continue

        # required?
        required = False
        try:
            required = bool(field.is_required())
        except Exception:
            required = getattr(field, "default", None) is None and getattr(field, "default_factory", None) is None

        if not required:
            continue

        ann = getattr(field, "annotation", None)

        # Nested BaseModel -> recurse
        try:
            if isinstance(ann, type) and issubclass(ann, BaseModel):
                payload[key] = _mk_pydantic_payload(ann, {})
                continue
        except Exception:
            pass

        # typing.List[...] / typing.Dict[...] fallbacks
        try:
            from typing import get_origin

            origin = get_origin(ann)
            if origin is list:
                payload[key] = []
                continue
            if origin is dict:
                payload[key] = {}
                continue
        except Exception:
            pass

        payload[key] = _default_for_field(field)

    # Validate locally to ensure the server will parse it as Proposal(**payload)
    Model(**payload)
    return payload


def _mk_proposal_payload(Proposal, *, src_val_id: str, chain_id: str) -> Dict[str, Any]:
    """
    Fill common consensus fields with sensible values; everything else is generic.
    """
    overrides: Dict[str, Any] = {}

    # common ids
    for k in ("proposer", "proposer_val_id", "leader", "val_id", "from_val_id"):
        overrides[k] = (src_val_id or "").strip() or "val1"

    # common proposal coordinates
    overrides["height"] = 1
    overrides["round"] = 0

    # common proposal id / block id
    overrides["block_id"] = "h1-r0-Ptest"
    overrides["proposal_id"] = "h1-r0-Ptest"

    # some models include chain_id inside the payload too
    overrides["chain_id"] = chain_id

    # roots are often hex-ish; keep them stable if required
    overrides["state_root"] = "00" * 32
    overrides["txs_root"] = "00" * 32

    return _mk_pydantic_payload(Proposal, overrides)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_p2p_proposal_sig_tamper_gate() -> None:
    nodes = await start_n_nodes(3, base_port=18080, chain_id="glyphchain-dev")
    try:
        Proposal = _import_proposal_model()

        src = nodes[0]  # signer identity (val1)
        dst = nodes[1]  # verifier node

        # Build a pydantic-valid proposal payload
        payload = _mk_proposal_payload(Proposal, src_val_id=src.val_id, chain_id=src.chain_id)

        # Sign it with the node’s deterministic test privkey
        sig_msg = canonical_p2p_sign_bytes(msg_type="PROPOSAL", chain_id=src.chain_id, payload=payload)
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

        # Ensure tampered payload is still pydantic-valid (we only want signature to fail)
        Proposal(**tampered)

        env = {
            "type": "PROPOSAL",
            "from_node_id": src.node_id,
            "from_val_id": src.val_id,
            "chain_id": src.chain_id,
            "ts_ms": _now_ms(),
            "payload": tampered,
            "hops": 0,
        }

        r = await http_post(dst.base_url, "/api/p2p/proposal", env, timeout_s=6.0)
        assert int(r.get("status") or 0) == 403, f"expected 403 on tampered sig, got: {r}"

    finally:
        await stop_nodes(nodes)