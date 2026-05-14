from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


def _state_path() -> str:
    # per-node local file (keeps tests isolated by env)
    base = (os.getenv("GLYPHCHAIN_STATE_DIR", "") or "").strip()
    if base:
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, "consensus_state.json")
    return (os.getenv("CONSENSUS_STATE_PATH", "") or "consensus_state.json").strip()


@dataclass
class PersistedConsensusState:
    finalized_height: int = 0
    last_qc: Optional[Dict[str, Any]] = None


def load_state() -> PersistedConsensusState:
    path = _state_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            j = json.load(f)
        if not isinstance(j, dict):
            return PersistedConsensusState()
        fh = int(j.get("finalized_height") or 0)
        qc = j.get("last_qc")
        return PersistedConsensusState(finalized_height=fh, last_qc=(qc if isinstance(qc, dict) else None))
    except Exception:
        return PersistedConsensusState()


def save_state(finalized_height: int, last_qc: Optional[Dict[str, Any]]) -> None:
    path = _state_path()
    tmp = path + ".tmp"
    j = {"finalized_height": int(finalized_height), "last_qc": (last_qc if isinstance(last_qc, dict) else None)}
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(j, f, separators=(",", ":"), sort_keys=True)
        os.replace(tmp, path)
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass