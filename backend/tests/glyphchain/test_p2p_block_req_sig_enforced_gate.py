# backend/tests/test_p2p_block_req_sig_enforced_gate.py
from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

import pytest
pytestmark = [pytest.mark.integration, pytest.mark.glyphchain]

from backend.tests.helpers import start_n_nodes, stop_nodes, http_get, http_post
from backend.modules.p2p.crypto_ed25519 import (
    canonical_p2p_sign_bytes,
    canonical_hello_sign_bytes,
    sign_ed25519,
)

def _now_ms() -> float:
    return float(time.time() * 1000.0)

def _mk_env(*, typ: str, src, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": typ,
        "from_node_id": src.node_id,
        "from_val_id": src.val_id,
        "chain_id": src.chain_id,
        "ts_ms": _now_ms(),
        "payload": payload,
        "hops": 0,
    }

async def _post(dst_base: str, path: str, env: Dict[str, Any]) -> Dict[str, Any]:
    return await http_post(dst_base, path, env, timeout_s=8.0)

async def _send_hello(dst_base: str, *, src, base_url: str) -> Dict[str, Any]:
    pubkey_hex = (getattr(src, "p2p_pubkey_hex", "") or "").strip().lower()
    assert pubkey_hex, "src missing p2p_pubkey_hex (start_n_nodes must expose it)"

    msg = canonical_hello_sign_bytes(
        chain_id=src.chain_id,
        node_id=src.node_id,
        val_id=src.val_id,
        base_url=base_url,
        pubkey_hex=pubkey_hex,
    )
    sig_hex = sign_ed25519(src.p2p_privkey_hex, msg)

    payload = {
        "base_url": base_url,
        "val_id": src.val_id,
        "pubkey_hex": pubkey_hex,
        "sig_hex": sig_hex,
    }
    env = {
        "type": "HELLO",
        "from_node_id": src.node_id,
        "from_val_id": src.val_id,
        "chain_id": src.chain_id,
        "ts_ms": _now_ms(),
        "payload": payload,
        "hops": 0,
        "base_url": base_url,
        "role": "peer",
    }
    return await _post(dst_base, "/api/p2p/hello", env)

def _sign_block_req(*, chain_id: str, src, payload_wo_sig: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(payload_wo_sig)
    msg = canonical_p2p_sign_bytes(msg_type="BLOCK_REQ", chain_id=chain_id, payload=payload)
    payload["sig_hex"] = sign_ed25519(src.p2p_privkey_hex, msg)
    return payload

@pytest.mark.integration
@pytest.mark.asyncio
async def test_p2p_block_req_sig_enforced_gate() -> None:
    # Save/restore env so we don’t leak config into other tests
    keys = [
        "P2P_REQUIRE_SIGNED_BLOCK",
        "P2P_REQUIRE_HELLO_BINDING_BLOCK",
    ]
    old: Dict[str, Optional[str]] = {k: os.environ.get(k) for k in keys}

    os.environ["P2P_REQUIRE_SIGNED_BLOCK"] = "1"
    os.environ["P2P_REQUIRE_HELLO_BINDING_BLOCK"] = "1"

    nodes = await start_n_nodes(2, base_port=18420, chain_id="glyphchain-dev")
    try:
        dst = nodes[0]
        src = nodes[1]

        # dst must know src pubkey via signed HELLO (required when HELLO binding is on)
        rr = await _send_hello(dst.base_url, src=src, base_url=src.base_url)
        assert int(rr.get("status") or 0) == 200, f"HELLO failed: {rr}"

        # choose a height (it’s fine if it doesn’t exist; we accept 404 for valid sig)
        st = await http_get(dst.base_url, "/api/p2p/consensus_status", timeout_s=8.0)
        assert int(st.get("status") or 0) == 200, f"consensus_status failed: {st}"
        j = st.get("json") or {}
        h = int(j.get("finalized_height") or 0) or 1

        # 1) Missing sig_hex => 403
        payload = {"height": h, "want": "header"}
        env = _mk_env(typ="BLOCK_REQ", src=src, payload=payload)
        rr = await _post(dst.base_url, "/api/p2p/block_req", env)
        assert int(rr.get("status") or 0) == 403, f"expected 403 missing sig_hex: {rr}"

        # 2) Bad sig_hex => 403
        payload = {"height": h, "want": "header", "sig_hex": "00" * 64}
        env = _mk_env(typ="BLOCK_REQ", src=src, payload=payload)
        rr = await _post(dst.base_url, "/api/p2p/block_req", env)
        assert int(rr.get("status") or 0) == 403, f"expected 403 bad sig_hex: {rr}"

        # 3) Valid signature => 200 (ok) OR 404 (not found)
        payload_wo = {"height": h, "want": "header", "ts_ms": _now_ms()}
        payload = _sign_block_req(chain_id=dst.chain_id, src=src, payload_wo_sig=payload_wo)
        env = _mk_env(typ="BLOCK_REQ", src=src, payload=payload)
        rr = await _post(dst.base_url, "/api/p2p/block_req", env)

        code = int(rr.get("status") or 0)
        if code == 200:
            out = rr.get("json") or {}
            assert out.get("ok") is True, f"expected ok:true: {rr}"
            assert int(out.get("height") or 0) == h, f"height mismatch: {rr}"
            assert "header" in out, f"expected header in response: {rr}"
        elif code == 404:
            detail = ""
            try:
                detail = str((rr.get("json") or {}).get("detail") or rr.get("detail") or rr.get("text") or "")
            except Exception:
                detail = str(rr)
            assert "block not found" in detail.lower(), f"expected not-found detail: {rr}"
        else:
            raise AssertionError(f"expected 200 or 404 for valid signature, got {rr}")

    finally:
        await stop_nodes(nodes)
        # restore env
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v