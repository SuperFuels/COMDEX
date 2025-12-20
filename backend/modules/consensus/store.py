from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class ConsensusState:
    finalized_height: int = 0
    last_qc: Optional[Dict[str, Any]] = None
    round: int = 0


def _state_dir() -> Path:
    d = (os.getenv("GLYPHCHAIN_STATE_DIR", "") or "").strip()
    if d:
        return Path(d)
    # safe default for dev; tests should pass GLYPHCHAIN_STATE_DIR explicitly
    return Path(".glyphchain_state")


def _state_path() -> Path:
    return _state_dir() / "consensus_state.json"


def load_state() -> ConsensusState:
    p = _state_path()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return ConsensusState()
        return ConsensusState(
            finalized_height=int(raw.get("finalized_height") or 0),
            last_qc=(raw.get("last_qc") if isinstance(raw.get("last_qc"), dict) else None),
            round=int(raw.get("round") or 0),
        )
    except FileNotFoundError:
        return ConsensusState()
    except Exception:
        # corrupt file -> start fresh (don’t crash node)
        return ConsensusState()


def save_state(finalized_height: int, last_qc: Optional[Dict[str, Any]], round: int = 0) -> None:
    d = _state_dir()
    d.mkdir(parents=True, exist_ok=True)

    tmp = _state_path().with_suffix(".json.tmp")
    out = {
        "finalized_height": int(finalized_height),
        "last_qc": last_qc,
        "round": int(round),
    }
    tmp.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(_state_path())