from __future__ import annotations

from typing import Any, Dict, Optional

import httpx


_P2P_HDR_NODE = "x-glyphchain-p2p-node-id"
_P2P_HDR_VAL = "x-glyphchain-p2p-val-id"
_P2P_HDR_CHAIN = "x-glyphchain-p2p-chain-id"


def _merge_headers(base: Optional[Dict[str, str]], extra: Dict[str, str]) -> Dict[str, str]:
    out: Dict[str, str] = dict(base or {})
    # only set if not already present
    for k, v in extra.items():
        if v and k not in out:
            out[k] = v
    return out


async def post_json(
    base_url: str,
    path: str,
    body: Dict[str, Any],
    *,
    timeout_s: float = 5.0,
    headers: Optional[Dict[str, str]] = None,
    # convenience: attach relay headers without repeating dict assembly everywhere
    add_p2p_headers: bool = False,
    p2p_from_node_id: str = "",
    p2p_from_val_id: str = "",
    p2p_chain_id: str = "",
) -> Dict[str, Any]:
    """
    Small HTTP helper used by p2p/router.py.

    NOTE: Historically some callers expected "status" while others expected "status_code".
    We return BOTH to avoid subtle breakage.
    Returns: {status, status_code, json, text}
    """
    url = (base_url or "").rstrip("/") + path

    hdrs = dict(headers or {})
    if add_p2p_headers:
        extra: Dict[str, str] = {}
        if (p2p_from_node_id or "").strip():
            extra[_P2P_HDR_NODE] = (p2p_from_node_id or "").strip()
        if (p2p_from_val_id or "").strip():
            extra[_P2P_HDR_VAL] = (p2p_from_val_id or "").strip()
        if (p2p_chain_id or "").strip():
            extra[_P2P_HDR_CHAIN] = (p2p_chain_id or "").strip()
        hdrs = _merge_headers(hdrs, extra)

    async with httpx.AsyncClient(timeout=timeout_s) as client:
        r = await client.post(url, json=body, headers=hdrs)
        try:
            j = r.json()
        except Exception:
            j = None

        code = int(r.status_code)
        return {"status": code, "status_code": code, "json": j, "text": r.text}


async def get_json(
    base_url: str,
    path: str,
    *,
    timeout_s: float = 5.0,
    headers: Optional[Dict[str, str]] = None,
    # convenience: attach relay headers (useful for peer auth later)
    add_p2p_headers: bool = False,
    p2p_from_node_id: str = "",
    p2p_from_val_id: str = "",
    p2p_chain_id: str = "",
) -> Dict[str, Any]:
    """
    Small HTTP GET helper.

    NOTE: Historically some callers expected "status" while others expected "status_code".
    We return BOTH to avoid subtle breakage.
    Returns: {status, status_code, json, text}
    """
    url = (base_url or "").rstrip("/") + path

    hdrs = dict(headers or {})
    if add_p2p_headers:
        extra: Dict[str, str] = {}
        if (p2p_from_node_id or "").strip():
            extra[_P2P_HDR_NODE] = (p2p_from_node_id or "").strip()
        if (p2p_from_val_id or "").strip():
            extra[_P2P_HDR_VAL] = (p2p_from_val_id or "").strip()
        if (p2p_chain_id or "").strip():
            extra[_P2P_HDR_CHAIN] = (p2p_chain_id or "").strip()
        hdrs = _merge_headers(hdrs, extra)

    async with httpx.AsyncClient(timeout=timeout_s) as client:
        r = await client.get(url, headers=hdrs)
        try:
            j = r.json()
        except Exception:
            j = None

        code = int(r.status_code)
        return {"status": code, "status_code": code, "json": j, "text": r.text}


async def relay_submit_tx_async(
    base_url: str,
    body_dict: Dict[str, Any],
    *,
    from_node_id: str = "",
    from_val_id: str = "",
    chain_id: str = "",
    timeout_s: float = 10.0,
) -> Dict[str, Any]:
    """
    Relay to leader's /api/chain_sim/dev/submit_tx_async.

    Adds headers so leader can rate-limit and sanity-check relays:
      - x-glyphchain-p2p-node-id
      - x-glyphchain-p2p-val-id
      - x-glyphchain-p2p-chain-id
    """
    upstream = await post_json(
        base_url,
        "/api/chain_sim/dev/submit_tx_async",
        body_dict,
        timeout_s=timeout_s,
        add_p2p_headers=True,
        p2p_from_node_id=from_node_id,
        p2p_from_val_id=from_val_id,
        p2p_chain_id=chain_id,
    )

    # normalize to old shape expected by callers: {"status_code":..,"data":..}
    data = upstream.get("json")
    if not isinstance(data, dict):
        data = {"raw": upstream.get("text")}

    return {"status_code": int(upstream.get("status_code") or 0), "data": data}