from __future__ import annotations

from dataclasses import dataclass, asdict
from threading import RLock
from typing import Any, Dict, List, Optional

_LOCK = RLock()

@dataclass(frozen=True)
class ValidatorInfo:
    val_id: str
    pubkey_hex: str = ""
    power: int = 1
    p2p_addr: str = ""

_VALIDATORS: List[ValidatorInfo] = []

def set_validators(validators: List[Dict[str, Any]]) -> None:
    out: List[ValidatorInfo] = []
    for v in validators or []:
        if not isinstance(v, dict):
            continue
        val_id = (
            str(v.get("val_id") or "")
            or str(v.get("id") or "")
            or str(v.get("address") or "")
            or str(v.get("operator") or "")
        ).strip()
        if not val_id:
            continue
        out.append(
            ValidatorInfo(
                val_id=val_id,
                pubkey_hex=str(v.get("pubkey_hex") or v.get("pubkey") or "").strip(),
                power=int(v.get("power") or 1),
                p2p_addr=str(v.get("p2p_addr") or v.get("p2p") or "").strip(),
            )
        )
    out.sort(key=lambda x: x.val_id)
    with _LOCK:
        global _VALIDATORS
        _VALIDATORS = out

def get_validators() -> List[ValidatorInfo]:
    with _LOCK:
        return list(_VALIDATORS)

def get_validators_dict() -> List[Dict[str, Any]]:
    return [asdict(v) for v in get_validators()]

def leader_for_height(height: int) -> Optional[ValidatorInfo]:
    h = int(height or 0)
    if h <= 0:
        return None
    vals = get_validators()
    if not vals:
        return None
    idx = (h - 1) % len(vals)
    return vals[idx]
