from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

def _as_int(x: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        if x is None:
            return default
        if isinstance(x, bool):
            return default
        return int(x)
    except Exception:
        return default

def validate_vote_payload_or_error(p: Any) -> Optional[str]:
    if not isinstance(p, dict):
        return "bad vote payload (not a dict)"

    h = _as_int(p.get("height"), None)
    r = _as_int(p.get("round"), None)
    vt = p.get("vote_type")
    voter = str(p.get("voter") or "").strip()
    bid = str(p.get("block_id") or "").strip()

    if h is None or h <= 0:
        return "height must be > 0"
    if r is None or r < 0:
        return "round must be >= 0"
    if vt not in ("PREVOTE", "PRECOMMIT"):
        return "bad vote_type"
    if not voter or not bid:
        return "block_id and voter required"

    # sig_hex is optional unless your policy requires it; don’t enforce here.
    return None

def validate_qc_dict_or_error(qc_d: Any) -> Optional[str]:
    if not isinstance(qc_d, dict):
        return "bad qc (not a dict)"

    h = _as_int(qc_d.get("height"), None)
    r = _as_int(qc_d.get("round"), None)
    vt = qc_d.get("vote_type")
    bid = str(qc_d.get("block_id") or "").strip()
    voters = qc_d.get("voters")

    if h is None or h <= 0:
        return "qc.height must be > 0"
    if r is None or r < 0:
        return "qc.round must be >= 0"
    if vt not in ("PRECOMMIT",):
        return "qc.vote_type must be PRECOMMIT"
    if not bid:
        return "qc.block_id required"
    if not isinstance(voters, list) or not all(isinstance(x, str) and x.strip() for x in voters):
        return "qc.voters must be a list[str]"

    return None