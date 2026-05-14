# backend/modules/chain_sim/chain_sim_config.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from threading import RLock
from typing import Any, Dict, Optional

# ✅ RLock prevents self-deadlock if a function calls another that also locks.
_LOCK = RLock()

DEFAULT_CHAIN_ID = "glyphchain-dev"
DEFAULT_NETWORK_ID = "devnet"  # change if you truly want "local"


@dataclass
class DevChainConfig:
    chain_id: str = DEFAULT_CHAIN_ID
    network_id: str = DEFAULT_NETWORK_ID


_CONFIG = DevChainConfig()


def _normalize_nonempty(v: Optional[str], fallback: str) -> str:
    s = (v or "").strip()
    return s if s else fallback


def get_config() -> Dict[str, Any]:
    """
    Thread-safe getter. Hardens against empty chain_id/network_id.
    Returns a normalized dict copy.
    """
    with _LOCK:
        _CONFIG.chain_id = _normalize_nonempty(_CONFIG.chain_id, DEFAULT_CHAIN_ID)
        _CONFIG.network_id = _normalize_nonempty(_CONFIG.network_id, DEFAULT_NETWORK_ID)

        out = asdict(_CONFIG)
        out["chain_id"] = _normalize_nonempty(out.get("chain_id"), DEFAULT_CHAIN_ID)
        out["network_id"] = _normalize_nonempty(out.get("network_id"), DEFAULT_NETWORK_ID)
        return out


def set_config(*, chain_id: Optional[str] = None, network_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Thread-safe setter. Never calls get_config() while holding a non-reentrant lock.
    (We use RLock anyway, but we still avoid nested locking by design.)
    """
    with _LOCK:
        if chain_id is not None:
            _CONFIG.chain_id = _normalize_nonempty(str(chain_id), DEFAULT_CHAIN_ID)
        else:
            _CONFIG.chain_id = _normalize_nonempty(_CONFIG.chain_id, DEFAULT_CHAIN_ID)

        if network_id is not None:
            _CONFIG.network_id = _normalize_nonempty(str(network_id), DEFAULT_NETWORK_ID)
        else:
            _CONFIG.network_id = _normalize_nonempty(_CONFIG.network_id, DEFAULT_NETWORK_ID)

        # ✅ return normalized snapshot directly (no nested get_config call needed)
        out = asdict(_CONFIG)
        out["chain_id"] = _normalize_nonempty(out.get("chain_id"), DEFAULT_CHAIN_ID)
        out["network_id"] = _normalize_nonempty(out.get("network_id"), DEFAULT_NETWORK_ID)
        return out


def reset_config() -> None:
    with _LOCK:
        _CONFIG.chain_id = DEFAULT_CHAIN_ID
        _CONFIG.network_id = DEFAULT_NETWORK_ID