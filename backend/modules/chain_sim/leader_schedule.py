from __future__ import annotations
from typing import Optional, Dict, Any, List
import hashlib

def _as_list_validators(vals: Any) -> List[Dict[str, Any]]:
    if isinstance(vals, list):
        return [v for v in vals if isinstance(v, dict)]
    return []

def leader_for_height(height: int, *, salt: str = "glyphchain-dev") -> Optional[str]:
    """
    Deterministic leader schedule:
      leader_index = height % N
    Uses validator_registry.get_validators() if available.
    Returns validator address or None.
    """
    if int(height or 0) <= 0:
        return None

    from backend.modules.chain_sim import validator_registry as vr

    vals = None
    if hasattr(vr, "get_validators"):
        vals = vr.get_validators()
    else:
        # fallback if registry is minimal: expose internal list differently
        vals = getattr(vr, "_VALIDATORS", None)

    vlist = _as_list_validators(vals)
    if not vlist:
        return None

    # stable ordering by address
    vlist.sort(key=lambda v: str(v.get("address") or ""))

    n = len(vlist)
    idx = int(height) % n
    return str(vlist[idx].get("address") or "") or None