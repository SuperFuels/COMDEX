from __future__ import annotations

import json
import os
import threading
import time
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
        nid = vid or _norm_base_url(base_url) or "peer"

    base = _norm_base_url(base_url)
    role = (role or "peer").strip()

    with _PEERS_LOCK:
        # ✅ MERGE into existing peer (DO NOT reset pubkey_hex / hello_ok)
        existing = _PEERS_BY_NODE_ID.get(nid)
        if existing is not None:
            try:
                if base:
                    existing.base_url = base
            except Exception:
                pass

            try:
                if role:
                    existing.role = role
            except Exception:
                pass

            # only update val_id if provided (avoid wiping)
            if vid:
                try:
                    existing.val_id = vid
                except Exception:
                    pass
                _PEERS_BY_VAL_ID[vid] = existing

            return existing

        # ✅ NEW peer
        p = PeerInfo(
            node_id=nid,
            base_url=base,
            val_id=(vid or None),
            role=role,
        )

        # identity fields default only for NEW peers
        for k, v in (
            ("pubkey_hex", None),
            ("hello_ok", False),
            ("last_hello_ms", None),
        ):
            try:
                if hasattr(p, k):
                    setattr(p, k, v)
            except Exception:
                pass

        _PEERS_BY_NODE_ID[nid] = p
        if vid:
            _PEERS_BY_VAL_ID[vid] = p
        return p


def list_peers() -> List[PeerInfo]:
    with _PEERS_LOCK:
        return list(_PEERS_BY_NODE_ID.values())


def get_peer(node_id: str) -> Optional[PeerInfo]:
    nid = (node_id or "").strip()
    if not nid:
        return None
    with _PEERS_LOCK:
        return _PEERS_BY_NODE_ID.get(nid)


def get_peer_by_node_id(node_id: str) -> Optional[PeerInfo]:
    return get_peer(node_id)


def find_peer_by_val_id(val_id: str) -> Optional[PeerInfo]:
    vid = (val_id or "").strip()
    if not vid:
        return None
    with _PEERS_LOCK:
        p = _PEERS_BY_VAL_ID.get(vid)
        if p and not getattr(p, "banned", False):
            return p
        return None


def set_peer_identity(
    *,
    node_id: str,
    base_url: str,
    val_id: Optional[str],
    pubkey_hex: str,
    hello_ok: bool,
) -> None:
    """
    Update (or create) a peer record with a verified pubkey binding.
    Best-effort: never raises.
    """
    try:
        nid = (node_id or "").strip()
        if not nid:
            return

        burl = _norm_base_url(base_url)
        vid = (str(val_id).strip() if val_id is not None else "")
        pk = (pubkey_hex or "").strip().lower()

        with _PEERS_LOCK:
            p = _PEERS_BY_NODE_ID.get(nid)

            if p is None:
                # IMPORTANT: do NOT call add_peer() while holding the lock (deadlock).
                p = PeerInfo(
                    node_id=nid,
                    base_url=burl,
                    val_id=(vid or None),
                    role="peer",
                )
                # identity defaults if fields exist
                try:
                    if hasattr(p, "pubkey_hex") and getattr(p, "pubkey_hex", None) is None:
                        setattr(p, "pubkey_hex", None)
                except Exception:
                    pass
                try:
                    if hasattr(p, "hello_ok") and getattr(p, "hello_ok", None) is None:
                        setattr(p, "hello_ok", False)
                except Exception:
                    pass
                try:
                    if hasattr(p, "last_hello_ms") and getattr(p, "last_hello_ms", None) is None:
                        setattr(p, "last_hello_ms", None)
                except Exception:
                    pass

                _PEERS_BY_NODE_ID[nid] = p
                if vid:
                    _PEERS_BY_VAL_ID[vid] = p

            # update base_url / val_id
            if burl:
                try:
                    p.base_url = burl
                except Exception:
                    pass

            if vid:
                # update val mapping coherently
                try:
                    old_vid = (getattr(p, "val_id", None) or "").strip()
                except Exception:
                    old_vid = ""

                try:
                    p.val_id = vid
                except Exception:
                    pass

                if old_vid and old_vid != vid:
                    try:
                        cur = _PEERS_BY_VAL_ID.get(old_vid)
                        if cur is p:
                            _PEERS_BY_VAL_ID.pop(old_vid, None)
                    except Exception:
                        pass

                _PEERS_BY_VAL_ID[vid] = p

            # identity fields
            if pk and hasattr(p, "pubkey_hex"):
                try:
                    setattr(p, "pubkey_hex", pk)
                except Exception:
                    pass

            if hasattr(p, "hello_ok"):
                try:
                    setattr(p, "hello_ok", bool(hello_ok))
                except Exception:
                    pass

            if hasattr(p, "last_hello_ms"):
                try:
                    setattr(p, "last_hello_ms", float(time.time() * 1000.0))
                except Exception:
                    pass

    except Exception:
        return


def load_peers_from_env() -> None:
    """
    Merge peers from:
      P2P_PEERS_JSON='[
        {"node_id":"n1","base_url":"http://127.0.0.1:8080","val_id":"val1","role":"validator"},
        {"node_id":"n2","base_url":"http://127.0.0.1:8081","val_id":"val2","role":"validator"}
      ]'

    IMPORTANT:
      - Non-destructive + idempotent.
      - Safe to call repeatedly; does not wipe hello_ok/pubkey_hex anymore because add_peer merges.
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
        role = str(it.get("role") or "peer").strip() or "peer"
        if not base_url:
            continue

        add_peer(
            base_url=base_url,
            node_id=node_id,
            val_id=(str(val_id).strip() if val_id is not None else None),
            role=role,
        )