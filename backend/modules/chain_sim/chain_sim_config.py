# backend/modules/chain_sim/chain_sim_config.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from threading import Lock
from typing import Any, Dict, Optional

_LOCK = Lock()


@dataclass
class DevChainConfig:
    chain_id: str = "comdex-dev"
    network_id: str = "local"


_CONFIG = DevChainConfig()


def get_config() -> Dict[str, Any]:
    with _LOCK:
        return asdict(_CONFIG)


def set_config(*, chain_id: Optional[str] = None, network_id: Optional[str] = None) -> Dict[str, Any]:
    with _LOCK:
        if chain_id is not None:
            _CONFIG.chain_id = str(chain_id)
        if network_id is not None:
            _CONFIG.network_id = str(network_id)
        return asdict(_CONFIG)


def reset_config() -> None:
    with _LOCK:
        _CONFIG.chain_id = "comdex-dev"
        _CONFIG.network_id = "local"