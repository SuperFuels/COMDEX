from __future__ import annotations

import os
from pathlib import Path
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


async def post_file(
    base_url: str,
    path: str,
    body: Dict[str, Any],
    *,
    output_path: str | Path,
    expected_media_type: str,
    max_bytes: int,
    timeout_s: float = 120.0,
    headers: Optional[Dict[str, str]] = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> Dict[str, Any]:
    """Stream a bounded peer response to an owner-only file without redirects."""
    url = (base_url or "").rstrip("/") + path
    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    written = 0
    try:
        timeout = httpx.Timeout(timeout_s, connect=min(10.0, timeout_s))
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=False, transport=transport,
        ) as client:
            async with client.stream("POST", url, json=body, headers=dict(headers or {})) as response:
                if response.status_code != 200:
                    content = await response.aread()
                    raise RuntimeError(f"peer_snapshot_http_{response.status_code}:{content[:512].decode('utf-8', 'replace')}")
                media_type = str(response.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
                if media_type != str(expected_media_type).strip().lower():
                    raise RuntimeError("peer_snapshot_media_type_invalid")
                try:
                    declared = int(response.headers.get("content-length") or 0)
                except ValueError:
                    declared = 0
                if declared > int(max_bytes):
                    raise RuntimeError("peer_snapshot_size_exceeded")
                with temporary.open("xb") as stream:
                    async for chunk in response.aiter_bytes(1024 * 1024):
                        written += len(chunk)
                        if written > int(max_bytes):
                            raise RuntimeError("peer_snapshot_size_exceeded")
                        stream.write(chunk)
                    stream.flush()
                    os.fsync(stream.fileno())
                if written <= 0:
                    raise RuntimeError("peer_snapshot_empty")
                os.chmod(temporary, 0o600)
                os.replace(temporary, output)
                return {
                    "status": 200,
                    "status_code": 200,
                    "bytes": written,
                    "snapshot_id": str(response.headers.get("x-glyphchain-snapshot-id") or ""),
                    "snapshot_height": str(response.headers.get("x-glyphchain-snapshot-height") or ""),
                }
    finally:
        temporary.unlink(missing_ok=True)


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
