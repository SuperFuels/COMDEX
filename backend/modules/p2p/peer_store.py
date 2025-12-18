from __future__ import annotations

import json
import os
import threading
from typing import Dict, Optional, List

from .p2p_types import PeerInfo


_PEERS_LOCK = threading.Lock()
_PEERS_BY_NODE_ID: Dict[str, PeerInfo] = {}
_PEERS_BY_VAL_ID: Dict[str, PeerInfo] = {}


def _norm_base_url(url: str) -> str:
    return (url or "").strip().rstrip("/")


def add_peer(
    base_url: str,
    node_id: str,
    val_id: Optional[str] = None,
    role: str = "peer",
) -> PeerInfo:
    nid = (node_id or "").strip()
    vid = (val_id or "").strip() if val_id is not None else ""
    if not nid:
        # dev convenience: allow node_id omitted if val_id present
        nid = vid or _norm_base_url(base_url) or "peer"
    p = PeerInfo(node_id=nid, base_url=_norm_base_url(base_url), val_id=(vid or None), role=(role or "peer"))

    with _PEERS_LOCK:
        _PEERS_BY_NODE_ID[nid] = p
        if vid:
            _PEERS_BY_VAL_ID[vid] = p
    return p


def list_peers() -> List[PeerInfo]:
    with _PEERS_LOCK:
        # stable-ish output
        return list(_PEERS_BY_NODE_ID.values())


def get_peer(node_id: str) -> Optional[PeerInfo]:
    nid = (node_id or "").strip()
    if not nid:
        return None
    with _PEERS_LOCK:
        return _PEERS_BY_NODE_ID.get(nid)


def find_peer_by_val_id(val_id: str) -> Optional[PeerInfo]:
    vid = (val_id or "").strip()
    if not vid:
        return None
    with _PEERS_LOCK:
        p = _PEERS_BY_VAL_ID.get(vid)
        if p and not p.banned:
            return p
        return None


def load_peers_from_env() -> None:
    """
    Optional bootstrap:
      P2P_PEERS_JSON='[
        {"node_id":"n1","base_url":"http://127.0.0.1:8080","val_id":"pho1-dev-val1","role":"validator"},
        {"node_id":"n2","base_url":"http://127.0.0.1:8081","val_id":"pho1-dev-val2","role":"validator"}
      ]'
    """
    raw = (os.getenv("P2P_PEERS_JSON", "") or "").strip()
    if not raw:
        return
    try:
        items = json.loads(raw)
    except Exception:
        return
    if not isinstance(items, list):
        return

    for it in items:
        if not isinstance(it, dict):
            continue
        base_url = str(it.get("base_url") or "").strip()
        node_id = str(it.get("node_id") or "").strip()
        val_id = it.get("val_id")
        role = str(it.get("role") or "peer").strip()
        if not base_url:
            continue
        add_peer(
            base_url=base_url,
            node_id=node_id,
            val_id=(str(val_id).strip() if val_id is not None else None),
            role=role,
        )