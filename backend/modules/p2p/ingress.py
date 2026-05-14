# backend/modules/p2p/ingress.py
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict

from backend.modules.p2p.lane_limiter import LaneLimiter

_LANES: LaneLimiter | None = None

def get_lanes() -> LaneLimiter:
    global _LANES
    if _LANES is None:
        _LANES = LaneLimiter.from_env()
    return _LANES

def _stable_json_bytes(x: Any) -> bytes:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def proposal_msg_id(payload: Dict[str, Any]) -> str:
    canon = {
        "height": int(payload.get("height") or 0),
        "round": int(payload.get("round") or 0),
        "proposer": str(payload.get("proposer") or ""),
        "block_id": str(payload.get("block_id") or ""),
    }
    return hashlib.sha256(_stable_json_bytes(canon)).hexdigest()

def vote_msg_id(payload: Dict[str, Any]) -> str:
    canon = {
        "height": int(payload.get("height") or 0),
        "round": int(payload.get("round") or 0),
        "vote_type": str(payload.get("vote_type") or "").upper(),
        "block_id": str(payload.get("block_id") or ""),
        "voter": str(payload.get("voter") or ""),
    }
    return hashlib.sha256(_stable_json_bytes(canon)).hexdigest()

def sync_msg_id(payload: Dict[str, Any]) -> str:
    # request-like; keep simple + stable
    canon = {
        "finalized_height": int(payload.get("finalized_height") or 0),
        "round": int(payload.get("round") or 0),
        "peer": str(payload.get("from_val_id") or payload.get("from_node_id") or ""),
    }
    return hashlib.sha256(_stable_json_bytes(canon)).hexdigest()

def block_req_msg_id(payload: Dict[str, Any]) -> str:
    canon = {
        "height": int(payload.get("height") or 0),
        "want": str(payload.get("want") or "block"),
        "peer": str(payload.get("from_val_id") or payload.get("from_node_id") or ""),
    }
    return hashlib.sha256(_stable_json_bytes(canon)).hexdigest()