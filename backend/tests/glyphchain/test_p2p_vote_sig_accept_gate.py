# backend/tests/test_p2p_vote_sig_accept_gate.py
from __future__ import annotations

import time
from typing import Any, Dict

import pytest
pytestmark = [pytest.mark.integration, pytest.mark.glyphchain]
import httpx

from backend.tests.helpers import start_n_nodes, stop_nodes, http_get
from backend.modules.p2p.crypto_ed25519 import (
    canonical_p2p_sign_bytes,
    canonical_hello_sign_bytes,
    sign_ed25519,
)


def _now_ms() -> float:
    return float(time.time() * 1000.0)


def _import_vote_model():
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
    ann = getattr(field, "annotation", None)

    try:
        from typing import get_origin, get_args, Literal
        if get_origin(ann) is Literal:
            args = list(get_args(ann) or [])
            if args:
                return args[0]
    except Exception:
        pass

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


def _mk_vote_payload(Vote, *, src_val_id: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}

    fields = getattr(Vote, "model_fields", None)
    if not isinstance(fields, dict) or not fields:
        raise RuntimeError("Vote model_fields not found (expected pydantic v2 model)")

    for name, field in fields.items():
        try:
            required = bool(field.is_required())
        except Exception:
            required = getattr(field, "default", None) is None and getattr(field, "default_factory", None) is None

        if not required:
            continue

        key = str(name)

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

    Vote(**payload)
    return payload


async def _hello_one(src, dst) -> None:
    """
    Send a signed HELLO from src -> dst and assert dst stores pubkey_hex + hello_ok.
    """
    msg = canonical_hello_sign_bytes(
        chain_id=src.chain_id,
        node_id=src.node_id,
        val_id=src.val_id,
        base_url=src.base_url,
        pubkey_hex=src.p2p_pubkey_hex,
    )
    sig_hex = sign_ed25519(src.p2p_privkey_hex, msg)

    env = {
        "type": "HELLO",
        "from_node_id": src.node_id,
        "from_val_id": src.val_id,
        "chain_id": src.chain_id,
        "ts_ms": _now_ms(),
        "payload": {
            "base_url": src.base_url,
            "val_id": src.val_id,
            "role": "peer",
            "pubkey_hex": src.p2p_pubkey_hex,
            "sig_hex": sig_hex,
        },
        "hops": 0,
    }

    headers = {
        "x-p2p-node-id": src.node_id,
        "x-p2p-val-id": src.val_id,
        "x-p2p-chain-id": src.chain_id,
    }

    async with httpx.AsyncClient(timeout=6.0) as c:
        r = await c.post(dst.base_url.rstrip("/") + "/api/p2p/hello", json=env, headers=headers)
        j = None
        try:
            j = r.json()
        except Exception:
            pass
    assert int(r.status_code) == 200, f"HELLO expected 200, got status={r.status_code} json={j} text={r.text}"

    peers = await http_get(dst.base_url, "/api/p2p/peers", timeout_s=6.0)
    assert int(peers.get("status") or 0) == 200, f"/peers failed after HELLO: {peers}"
    pj = peers.get("json") or {}
    plist = (pj.get("peers") if isinstance(pj, dict) else None) or []
    rec = None
    for it in plist if isinstance(plist, list) else []:
        if isinstance(it, dict) and (it.get("node_id") or "") == src.node_id:
            rec = it
            break

    assert rec is not None, f"dst missing src in /peers: src={src.node_id} peers={plist}"
    assert (rec.get("pubkey_hex") or "").strip(), f"dst did not store src pubkey: {rec}"
    assert bool(rec.get("hello_ok")) is True, f"dst hello_ok not true for src: {rec}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_p2p_vote_sig_accept_gate() -> None:
    nodes = await start_n_nodes(3, base_port=18080, chain_id="glyphchain-dev")
    try:
        Vote = _import_vote_model()

        src = nodes[0]  # signer (val1)
        dst = nodes[1]  # verifier

        # Make HELLO explicit + asserted (don’t rely on helper best-effort)
        await _hello_one(src, dst)

        payload = _mk_vote_payload(Vote, src_val_id=src.val_id)

        sig_msg = canonical_p2p_sign_bytes(msg_type="VOTE", chain_id=src.chain_id, payload=payload)
        sig_hex = sign_ed25519(src.p2p_privkey_hex, sig_msg)

        payload_signed = dict(payload)
        payload_signed["sig_hex"] = sig_hex

        env = {
            "type": "VOTE",
            "from_node_id": src.node_id,
            "from_val_id": src.val_id,
            "chain_id": src.chain_id,
            "ts_ms": _now_ms(),
            "payload": payload_signed,
            "hops": 0,
        }

        headers = {
            "x-p2p-node-id": src.node_id,
            "x-p2p-val-id": src.val_id,
            "x-p2p-chain-id": src.chain_id,
        }

        async with httpx.AsyncClient(timeout=6.0) as c:
            r = await c.post(dst.base_url.rstrip("/") + "/api/p2p/vote", json=env, headers=headers)
            j = None
            try:
                j = r.json()
            except Exception:
                pass

        # This is an “auth/sig acceptance” gate:
        # consensus may still 400 for semantics (equivocation, wrong height, etc).
        assert int(r.status_code) != 403, f"expected not-403 (sig layer accepted), got 403: json={j} text={r.text}"

    finally:
        await stop_nodes(nodes)