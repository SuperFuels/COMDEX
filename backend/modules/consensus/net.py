# backend/modules/consensus/net.py
from __future__ import annotations

import os
import random
import time
from typing import Any, Dict, List, Optional
from backend.modules.p2p.crypto_ed25519 import (
    canonical_hello_sign_bytes,
    canonical_p2p_sign_bytes,
    pubkey_from_priv,
    sign_ed25519,
)
from backend.modules.p2p.peer_store import load_peers_from_env, list_peers
from backend.modules.p2p.transport_http import post_json
from backend.modules.p2p.nat_relay import active_transport_private_key, enqueue_via_nat_relay
from backend.modules.consensus.protocol_upgrade import local_protocol_advertisement


def _now_ms() -> float:
    return float(time.time() * 1000.0)


def _local_base_url() -> str:
    return (os.getenv("GLYPHCHAIN_BASE_URL", "") or "http://127.0.0.1:8080").strip().rstrip("/")


def _mk_env(
    *,
    msg_type: str,
    from_node_id: str,
    chain_id: str,
    payload: Dict[str, Any],
    from_val_id: Optional[str] = None,
    hops: int = 0,
) -> Dict[str, Any]:
    env: Dict[str, Any] = {
        "type": msg_type,
        "from_node_id": from_node_id,
        "chain_id": chain_id,
        "ts_ms": _now_ms(),
        "payload": payload,
        "hops": int(hops),
    }
    if from_val_id is not None:
        env["from_val_id"] = from_val_id
    return env


def _remote_peers_base_urls() -> List[str]:
    load_peers_from_env()
    local = _local_base_url()
    out: List[str] = []
    for p in list_peers():
        base = (getattr(p, "base_url", "") or "").strip().rstrip("/")
        if not base or base == local:
            continue
        out.append(base)
    return out


def _pick_peer_base_url() -> str:
    bases = _remote_peers_base_urls()
    if not bases:
        return ""
    return random.choice(bases)


async def _post_peer_or_nat_relay(
    peer: Any, *, path: str, envelope: Dict[str, Any], chain_id: str,
    from_node_id: str, from_val_id: str, timeout_s: float,
) -> Dict[str, Any]:
    base = (getattr(peer, "base_url", "") or "").strip().rstrip("/")
    target_node_id = (getattr(peer, "node_id", "") or "").strip()
    relay_url = (getattr(peer, "relay_url", "") or "").strip().rstrip("/")
    configured_relay = (os.getenv("GLYPHCHAIN_NAT_RELAY_URL", "") or "").strip().rstrip("/")
    if relay_url:
        return await enqueue_via_nat_relay(
            relay_url=relay_url, chain_id=chain_id, from_node_id=from_node_id,
            target_node_id=target_node_id, envelope=envelope,
        )
    try:
        response = await post_json(
            base, path, envelope, timeout_s=timeout_s,
            add_p2p_headers=True, p2p_from_node_id=from_node_id,
            p2p_from_val_id=from_val_id, p2p_chain_id=chain_id,
        )
        status = int(response.get("status") or 0)
        if 200 <= status < 300:
            return response
        raise RuntimeError(f"peer_http_{status}")
    except Exception:
        if not configured_relay or not target_node_id:
            raise
        return await enqueue_via_nat_relay(
            relay_url=configured_relay, chain_id=chain_id,
            from_node_id=from_node_id, target_node_id=target_node_id,
            envelope=envelope,
        )


async def ensure_peer_hello(
    *,
    chain_id: str,
    from_node_id: str,
    from_val_id: str,
    peer_base_url: str,
    finalized_height: int = 0,
) -> Dict[str, Any]:
    """Refresh the signed identity handshake before restart-sensitive sync.

    This is intentionally idempotent.  A node restored with FastAPI lifespan
    hooks disabled still re-establishes both sides of the HELLO binding before
    it requests consensus state or blocks.
    """
    priv = active_transport_private_key(chain_id=chain_id, node_id=from_node_id)
    base = (peer_base_url or "").strip().rstrip("/")
    local = _local_base_url()
    if not priv or not base or base == local:
        return {"ok": False, "skipped": True, "reason": "identity_or_remote_peer_unavailable"}
    pubkey = pubkey_from_priv(priv)
    protocol = local_protocol_advertisement(
        chain_id=chain_id, node_id=from_node_id, finalized_height=int(finalized_height),
    )
    msg = canonical_hello_sign_bytes(
        chain_id=chain_id,
        node_id=from_node_id,
        val_id=from_val_id,
        base_url=local,
        pubkey_hex=pubkey,
        protocol=protocol,
    )
    payload = {
        "base_url": local,
        "val_id": from_val_id,
        "role": "validator",
        "pubkey_hex": pubkey,
        "sig_hex": sign_ed25519(priv, msg),
        "is_reply": False,
        "protocol": protocol,
    }
    env = _mk_env(
        msg_type="HELLO",
        from_node_id=from_node_id,
        from_val_id=from_val_id,
        chain_id=chain_id,
        payload=payload,
    )
    env["base_url"] = local
    env["role"] = "validator"
    response = await post_json(base, "/api/p2p/hello", env, timeout_s=3.0)
    body = response.get("json") if isinstance(response, dict) else None
    return {
        "ok": bool(isinstance(body, dict) and body.get("ok") is True),
        "status": response.get("status") if isinstance(response, dict) else None,
        "peer_base_url": base,
    }


# -----------------------------------------------------------------------------
# broadcast helpers
# -----------------------------------------------------------------------------

async def broadcast_proposal(
    *,
    chain_id: str,
    from_node_id: str,
    from_val_id: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    load_peers_from_env()
    local = _local_base_url()

    # PR5.2: sign proposal payload (best-effort; only if privkey is configured)
    priv = active_transport_private_key(chain_id=chain_id, node_id=from_node_id)
    if priv:
        sig_msg = canonical_p2p_sign_bytes(msg_type="PROPOSAL", chain_id=chain_id, payload=payload)
        payload = dict(payload)
        payload["sig_hex"] = sign_ed25519(priv, sig_msg)

    env = _mk_env(
        msg_type="PROPOSAL",
        from_node_id=from_node_id,
        from_val_id=from_val_id,
        chain_id=chain_id,
        payload=payload,
    )

    sent = 0
    errs: list[str] = []

    for p in list_peers():
        base = (getattr(p, "base_url", "") or "").strip().rstrip("/")
        if not base or base == local:
            continue
        try:
            await _post_peer_or_nat_relay(
                p, path="/api/p2p/proposal", envelope=env, chain_id=chain_id,
                from_node_id=from_node_id, from_val_id=from_val_id, timeout_s=3.0,
            )
            sent += 1
        except Exception as e:
            # critical: never let one dead peer abort the broadcast
            errs.append(f"{base}: {type(e).__name__}: {e}")
            continue

    return {"ok": True, "sent": sent, "errors": errs}


async def broadcast_vote(
    *,
    chain_id: str,
    from_node_id: str,
    from_val_id: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    load_peers_from_env()
    local = _local_base_url()

    # PR5.2: sign vote payload (best-effort; only if privkey is configured)
    priv = active_transport_private_key(chain_id=chain_id, node_id=from_node_id)
    if priv:
        sig_msg = canonical_p2p_sign_bytes(msg_type="VOTE", chain_id=chain_id, payload=payload)
        payload = dict(payload)
        payload["sig_hex"] = sign_ed25519(priv, sig_msg)

    env = _mk_env(
        msg_type="VOTE",
        from_node_id=from_node_id,
        from_val_id=from_val_id,
        chain_id=chain_id,
        payload=payload,
    )

    sent = 0
    errs: list[str] = []

    for p in list_peers():
        base = (getattr(p, "base_url", "") or "").strip().rstrip("/")
        if not base or base == local:
            continue
        try:
            await _post_peer_or_nat_relay(
                p, path="/api/p2p/vote", envelope=env, chain_id=chain_id,
                from_node_id=from_node_id, from_val_id=from_val_id, timeout_s=3.0,
            )
            sent += 1
        except Exception as e:
            # critical: never let one dead peer abort the broadcast
            errs.append(f"{base}: {type(e).__name__}: {e}")
            continue

    return {"ok": True, "sent": sent, "errors": errs}


# -----------------------------------------------------------------------------
# PR4: sync helpers
# -----------------------------------------------------------------------------

async def request_status(*, chain_id: str, from_node_id: str, from_val_id: str) -> list[Dict[str, Any]]:
    """
    Legacy fanout status poll (kept for compatibility).
    Engine should prefer policy-backed single-peer polling if you wire it.
    """
    load_peers_from_env()
    out: list[Dict[str, Any]] = []

    env = _mk_env(
        msg_type="STATUS",
        from_node_id=from_node_id,
        from_val_id=from_val_id,
        chain_id=chain_id,
        payload={"want": "status"},
    )

    local = _local_base_url()
    for p in list_peers():
        base = (getattr(p, "base_url", "") or "").strip().rstrip("/")
        if not base or base == local:
            continue
        try:
            upstream = await post_json(
                base,
                "/api/p2p/status",
                env,
                timeout_s=3.0,
                add_p2p_headers=True,
                p2p_from_node_id=from_node_id,
                p2p_from_val_id=from_val_id,
                p2p_chain_id=chain_id,
            )
            j = upstream.get("json") if isinstance(upstream, dict) else None
            if isinstance(j, dict) and isinstance(j.get("payload"), dict):
                out.append(j["payload"])
        except Exception:
            pass

    return out


async def request_sync(*, chain_id: str, from_node_id: str, from_val_id: str) -> Dict[str, Any]:
    """
    Legacy fanout SYNC_REQ (kept for compatibility).
    Engine should NOT rely on this for policy/backoff; use request_sync_one() instead.
    """
    load_peers_from_env()
    responses: List[Dict[str, Any]] = []

    env = _mk_env(
        msg_type="SYNC_REQ",
        from_node_id=from_node_id,
        from_val_id=(from_val_id or None),
        chain_id=chain_id,
        payload={},
    )

    local = _local_base_url()
    for p in list_peers():
        base = (getattr(p, "base_url", "") or "").strip().rstrip("/")
        if not base or base == local:
            continue
        try:
            upstream = await post_json(
                base,
                "/api/p2p/sync_req",
                env,
                timeout_s=3.0,
                add_p2p_headers=True,
                p2p_from_node_id=from_node_id,
                p2p_from_val_id=from_val_id,
                p2p_chain_id=chain_id,
            )
            j = upstream.get("json") if isinstance(upstream, dict) else None
            if isinstance(j, dict) and j.get("ok") is True and isinstance(j.get("payload"), dict):
                peer_dump = getattr(p, "model_dump", None)
                peer_obj = peer_dump() if callable(peer_dump) else {"base_url": base}
                responses.append({"peer": peer_obj, "payload": j["payload"]})
        except Exception:
            continue

    return {"ok": True, "responses": responses}


async def request_sync_one(
    *,
    chain_id: str,
    from_node_id: str,
    from_val_id: str,
    peer_base_url: str,
) -> Dict[str, Any]:
    """
    Single-peer SYNC_REQ (engine uses this to apply SyncPolicy per-peer).
    Returns: {"ok": bool, "payload": dict|None, ...}
    """
    base = (peer_base_url or "").strip().rstrip("/")
    if not base:
        return {"ok": False, "error": "no peer_base_url"}

    env = _mk_env(
        msg_type="SYNC_REQ",
        from_node_id=from_node_id,
        from_val_id=(from_val_id or None),
        chain_id=chain_id,
        payload={},
    )

    upstream = await post_json(
        base,
        "/api/p2p/sync_req",
        env,
        timeout_s=3.0,
        add_p2p_headers=True,
        p2p_from_node_id=from_node_id,
        p2p_from_val_id=from_val_id,
        p2p_chain_id=chain_id,
    )

    j = upstream.get("json") if isinstance(upstream, dict) else None
    if isinstance(j, dict) and j.get("ok") is True and isinstance(j.get("payload"), dict):
        return {"ok": True, "payload": j["payload"], "peer_base_url": base, "status": upstream.get("status")}

    return {"ok": False, "error": "bad response", "peer_base_url": base, "status": upstream.get("status"), "json": j}


# -----------------------------------------------------------------------------
# PR4.2: block fetch helpers
# -----------------------------------------------------------------------------

async def request_block(
    *,
    chain_id: str,
    from_node_id: str,
    from_val_id: str,
    height: int,
    want: str = "block",
    peer_base_url: str | None = None,
) -> Dict[str, Any]:
    """
    Fetch a single block/header via /api/p2p/block_req.

    If peer_base_url is provided, targets that peer only.
    Else picks a peer from peer_store (best effort).
    """
    h = int(height or 0)
    if h <= 0:
        return {"ok": False, "error": "bad height"}

    w = (want or "block").strip().lower()
    if w not in ("block", "header"):
        w = "block"

    base = (peer_base_url or "").strip().rstrip("/")
    if not base:
        base = _pick_peer_base_url()

    if not base:
        return {"ok": False, "error": "no peers"}

    env = _mk_env(
        msg_type="BLOCK_REQ",
        from_node_id=from_node_id,
        from_val_id=from_val_id,
        chain_id=chain_id,
        payload={"height": h, "want": w},
    )

    upstream = await post_json(
        base,
        "/api/p2p/block_req",
        env,
        timeout_s=30.0,
        add_p2p_headers=True,
        p2p_from_node_id=from_node_id,
        p2p_from_val_id=from_val_id,
        p2p_chain_id=chain_id,
    )

    j = upstream.get("json") if isinstance(upstream, dict) else None
    if isinstance(j, dict):
        return j

    return {"ok": False, "error": "bad response", "peer_base_url": base, "status": upstream.get("status"), "text": upstream.get("text")}


async def request_blocks(
    *,
    chain_id: str,
    from_node_id: str,
    from_val_id: str,
    from_height: int,
    to_height: int,
    peer_base_url: str | None = None,
) -> Dict[str, Any]:
    """
    Best-effort sequential range fetch (single peer if peer_base_url provided).

    Returns:
      {"ok": True, "blocks": {height: block_dict, ...}, "missing": [h1, ...]}
    """
    a = int(from_height or 0)
    b = int(to_height or 0)
    if a <= 0 or b <= 0 or a > b:
        return {"ok": False, "error": "bad height range"}

    out: Dict[int, Dict[str, Any]] = {}
    missing: list[int] = []

    for h in range(a, b + 1):
        r = await request_block(
            chain_id=chain_id,
            from_node_id=from_node_id,
            from_val_id=from_val_id,
            height=h,
            want="block",
            peer_base_url=peer_base_url,
        )
        blk = r.get("block") if isinstance(r, dict) else None
        if isinstance(blk, dict):
            out[int(h)] = blk
        else:
            missing.append(int(h))

    return {"ok": True, "blocks": out, "missing": missing}
