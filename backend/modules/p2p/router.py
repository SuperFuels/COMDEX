from __future__ import annotations

import json
import os
from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException, Request

from backend.modules.chain_sim.chain_sim_ledger import get_block
from .p2p_types import P2PEnvelope
from .peer_store import add_peer, list_peers, load_peers_from_env
from .rate_limit import allow as rl_allow
from .transport_http import get_json, post_json

router = APIRouter()

_P2P_HDR_NODE = "x-glyphchain-p2p-node-id"
_P2P_HDR_VAL = "x-glyphchain-p2p-val-id"

_NODE_ID = (os.getenv("GLYPHCHAIN_NODE_ID", "") or os.getenv("P2P_NODE_ID", "") or "dev-node").strip()
_CHAIN_ID = (os.getenv("GLYPHCHAIN_CHAIN_ID", "") or os.getenv("CHAIN_ID", "") or "glyphchain-dev").strip()
_SELF_VAL_ID = (os.getenv("GLYPHCHAIN_SELF_VAL_ID", "") or "").strip()


def _local_base_url() -> str:
    return (os.getenv("GLYPHCHAIN_BASE_URL", "") or "http://127.0.0.1:8080").strip().rstrip("/")


def _approx_bytes(obj: Any) -> int:
    try:
        return len(json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    except Exception:
        return 0


def _rl_or_429(peer_key: str, payload_bytes: int) -> None:
    msg_rate = float(os.getenv("P2P_RL_MSG_PER_SEC", "50") or 50)
    msg_burst = float(os.getenv("P2P_RL_MSG_BURST", "100") or 100)
    byt_rate = float(os.getenv("P2P_RL_BYTES_PER_SEC", "512000") or 512000)     # 512KB/s
    byt_burst = float(os.getenv("P2P_RL_BYTES_BURST", "1048576") or 1048576)    # 1MB burst

    if not rl_allow(
        peer_key,
        cost_msgs=1.0,
        cost_bytes=float(payload_bytes),
        msg_rate_per_sec=msg_rate,
        msg_burst=msg_burst,
        bytes_rate_per_sec=byt_rate,
        bytes_burst=byt_burst,
    ):
        raise HTTPException(status_code=429, detail=f"rate limited (peer={peer_key})")


@router.get("/peers")
async def p2p_peers() -> Dict[str, Any]:
    load_peers_from_env()
    return {
        "ok": True,
        "node_id": _NODE_ID,
        "chain_id": _CHAIN_ID,
        "peers": [p.model_dump() for p in list_peers()],
    }


@router.post("/connect")
async def p2p_connect(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    load_peers_from_env()
    base_url = str(body.get("base_url") or body.get("url") or "").strip()
    node_id = str(body.get("node_id") or "").strip()
    val_id = body.get("val_id")
    role = str(body.get("role") or "peer")
    if not base_url or not node_id:
        raise HTTPException(status_code=400, detail="base_url and node_id required")
    p = add_peer(
        base_url=base_url,
        node_id=node_id,
        val_id=(str(val_id) if val_id is not None else None),
        role=role,
    )
    return {"ok": True, "added": True, "peer": p.model_dump()}


@router.post("/hello")
async def p2p_hello(env: P2PEnvelope = Body(...)) -> Dict[str, Any]:
    if env.type != "HELLO":
        raise HTTPException(status_code=400, detail="expected type=HELLO")
    if (env.chain_id or "").strip() != _CHAIN_ID:
        raise HTTPException(status_code=400, detail=f"chain_id mismatch (got={env.chain_id}, want={_CHAIN_ID})")

    base_url = str((env.base_url or env.payload.get("base_url") or "")).strip()
    node_id = str(env.from_node_id or "").strip()
    val_id = env.from_val_id or env.payload.get("val_id") or None
    role = str((env.role or env.payload.get("role") or "peer"))

    if not base_url or not node_id:
        raise HTTPException(status_code=400, detail="base_url and from_node_id required")

    load_peers_from_env()
    p = add_peer(
        base_url=base_url,
        node_id=node_id,
        val_id=(str(val_id) if val_id is not None else None),
        role=role,
    )
    return {
        "ok": True,
        "added": True,
        "peer": p.model_dump(),
        "peers": [x.model_dump() for x in list_peers()],
    }


@router.post("/refresh")
async def p2p_refresh(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    load_peers_from_env()
    target = str(body.get("base_url") or body.get("url") or "").strip().rstrip("/")
    if not target:
        raise HTTPException(status_code=400, detail="base_url required")

    upstream = await get_json(target, "/api/p2p/peers", timeout_s=8.0)
    j = upstream.get("json") or {}
    if not isinstance(j, dict) or not j.get("ok"):
        raise HTTPException(status_code=502, detail=f"upstream peers fetch failed: {upstream}")

    merged = 0
    for pj in (j.get("peers") or []):
        if not isinstance(pj, dict):
            continue
        base_url = str(pj.get("base_url") or "").strip()
        node_id = str(pj.get("node_id") or "").strip()
        if not base_url or not node_id:
            continue
        add_peer(
            base_url=base_url,
            node_id=node_id,
            val_id=(str(pj.get("val_id")) if pj.get("val_id") is not None else None),
            role=str(pj.get("role") or "peer"),
        )
        merged += 1

    return {"ok": True, "merged": merged, "peers": [p.model_dump() for p in list_peers()]}


@router.post("/tx_relay")
async def p2p_tx_relay(request: Request, env: P2PEnvelope = Body(...)) -> Dict[str, Any]:
    if env.type != "TX_RELAY":
        raise HTTPException(status_code=400, detail="expected type=TX_RELAY")
    if (env.chain_id or "").strip() != _CHAIN_ID:
        raise HTTPException(status_code=400, detail=f"chain_id mismatch (got={env.chain_id}, want={_CHAIN_ID})")

    peer_node = (request.headers.get(_P2P_HDR_NODE) or env.from_node_id or "").strip()
    peer_val = (request.headers.get(_P2P_HDR_VAL) or env.from_val_id or "").strip()
    peer_key = peer_val or peer_node or (getattr(request.client, "host", "") or "unknown")

    _rl_or_429(peer_key, _approx_bytes(env.model_dump()))

    tx = env.payload.get("tx") or env.payload.get("body") or {}
    if not isinstance(tx, dict):
        raise HTTPException(status_code=400, detail="payload.tx must be object")

    local_base = _local_base_url()
    upstream = await post_json(
        local_base,
        "/api/chain_sim/dev/submit_tx_async",
        tx,
        timeout_s=8.0,
        add_p2p_headers=True,
        p2p_from_node_id=(peer_node or env.from_node_id or "unknown"),
        p2p_from_val_id=(peer_val or _SELF_VAL_ID or ""),
        p2p_chain_id=_CHAIN_ID,
    )

    up_json = upstream.get("json")
    if isinstance(up_json, dict):
        out = dict(up_json)
        out["via_p2p"] = True
        out["p2p_from_node_id"] = env.from_node_id
        out["p2p_hops"] = env.hops
        return out

    return {"ok": True, "via_p2p": True, "upstream": upstream}


@router.post("/relay_tx")
async def p2p_relay_tx(request: Request, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    tx = body.get("tx") or body.get("body") or body
    if not isinstance(tx, dict):
        raise HTTPException(status_code=400, detail="tx must be object")

    env = P2PEnvelope(
        type="TX_RELAY",
        from_node_id=_NODE_ID,
        chain_id=_CHAIN_ID,
        ts_ms=float(body.get("ts_ms") or 0) or 0.0,
        payload={"tx": tx},
        hops=int(body.get("hops") or 0),
    )
    return await p2p_tx_relay(request, env)


# -------------------------
# Block announce + fetch
# -------------------------

@router.post("/block_announce")
async def p2p_block_announce(request: Request, env: P2PEnvelope = Body(...)) -> Dict[str, Any]:
    if env.type != "BLOCK_ANNOUNCE":
        raise HTTPException(status_code=400, detail="expected type=BLOCK_ANNOUNCE")
    if (env.chain_id or "").strip() != _CHAIN_ID:
        raise HTTPException(status_code=400, detail=f"chain_id mismatch (got={env.chain_id}, want={_CHAIN_ID})")

    peer_node = (request.headers.get(_P2P_HDR_NODE) or env.from_node_id or "").strip()
    peer_val = (request.headers.get(_P2P_HDR_VAL) or env.from_val_id or "").strip()
    peer_key = peer_val or peer_node or (getattr(request.client, "host", "") or "unknown")

    _rl_or_429(peer_key, _approx_bytes(env.model_dump()))

    h = int(env.payload.get("height") or 0)
    if h <= 0:
        raise HTTPException(status_code=400, detail="payload.height required")

    # Dev: just acknowledge receipt for now (later: trigger pull/fork-choice)
    return {"ok": True, "announced": True, "height": h}


@router.post("/block_req")
async def p2p_block_req(request: Request, env: P2PEnvelope = Body(...)) -> Dict[str, Any]:
    if env.type != "BLOCK_REQ":
        raise HTTPException(status_code=400, detail="expected type=BLOCK_REQ")
    if (env.chain_id or "").strip() != _CHAIN_ID:
        raise HTTPException(status_code=400, detail=f"chain_id mismatch (got={env.chain_id}, want={_CHAIN_ID})")

    peer_node = (request.headers.get(_P2P_HDR_NODE) or env.from_node_id or "").strip()
    peer_val = (request.headers.get(_P2P_HDR_VAL) or env.from_val_id or "").strip()
    peer_key = peer_val or peer_node or (getattr(request.client, "host", "") or "unknown")

    _rl_or_429(peer_key, _approx_bytes(env.model_dump()))

    h = int(env.payload.get("height") or 0)
    want = str(env.payload.get("want") or "block").strip().lower()
    if h <= 0:
        raise HTTPException(status_code=400, detail="payload.height required")
    if want not in ("block", "header"):
        raise HTTPException(status_code=400, detail='payload.want must be "block" or "header"')

    blk = get_block(h)
    if not blk:
        raise HTTPException(status_code=404, detail=f"block not found (height={h})")

    if want == "header":
        header = blk.get("header") or blk.get("block", {}).get("header") or {}
        return {"ok": True, "height": h, "header": header}

    return {"ok": True, "height": h, "block": blk}