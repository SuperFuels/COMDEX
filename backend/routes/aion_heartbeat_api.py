# backend/routes/aion_heartbeat_api.py
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

from fastapi import APIRouter

router = APIRouter(tags=["AION Heartbeat"])

ENV_DATA_ROOT = "TESSARIS_DATA_ROOT"

KNOWN_SENTINELS = [
    "control/aqci_log.jsonl",
    "control/rqfs_feedback.jsonl",
    "learning/fusion_state.jsonl",
    "aion_field/resonant_heartbeat.jsonl",
    "analysis/resonant_optimizer.jsonl",
    "analysis/state_resonance_log.jsonl",
]

def pick_data_root() -> Path:
    # 1) explicit override
    import os
    cwd = Path.cwd()
    if ENV_DATA_ROOT in os.environ:
        p = Path(os.environ[ENV_DATA_ROOT]).expanduser()
        if (p / "control").exists() or any((p / s).exists() for s in KNOWN_SENTINELS):
            return p

    # 2) prefer runtime-moved data if present
    candidates: List[Path] = []
    rt = cwd / ".runtime"
    if rt.exists():
        for d in rt.glob("*/data"):
            candidates.append(d)

    # 3) include local ./data
    candidates.append(cwd / "data")

    def score(d: Path) -> Tuple[int, float]:
        hits = 0
        newest = 0.0
        for s in KNOWN_SENTINELS:
            f = d / s
            if f.exists():
                hits += 1
                try:
                    newest = max(newest, f.stat().st_mtime)
                except Exception:
                    pass
        return (hits, newest)

    best = None
    best_score = (-1, -1.0)
    for d in candidates:
        sc = score(d)
        if sc > best_score:
            best = d
            best_score = sc

    return best if best else (cwd / "data")

def _tail_jsonl_last_obj(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        # cheap tail: read last ~64KB
        with path.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 65536), 0)
            chunk = f.read().decode("utf-8", errors="ignore")
        lines = [l.strip() for l in chunk.splitlines() if l.strip()]
        if not lines:
            return None
        return json.loads(lines[-1])
    except Exception:
        return None

def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def _latest_live_heartbeat_json(data_root: Path) -> Tuple[Optional[Dict[str, Any]], Optional[Path]]:
    hb_dir = data_root / "aion_field"
    if not hb_dir.exists():
        return (None, None)

    files = sorted(hb_dir.glob("*heartbeat_live.json"), key=lambda p: p.stat().st_mtime if p.exists() else 0.0)
    if not files:
        return (None, None)

    p = files[-1]
    return (_read_json(p), p)

@router.get("/heartbeat")
def get_heartbeat():
    data_root = pick_data_root()

    # 1) Preferred: MRTC-style jsonl heartbeat
    jsonl_path = data_root / "aion_field" / "resonant_heartbeat.jsonl"
    obj = _tail_jsonl_last_obj(jsonl_path)
    source_path: Optional[Path] = jsonl_path if obj else None

    # 2) Fallback: ResonanceHeartbeat live JSON snapshots
    if obj is None:
        obj2, p2 = _latest_live_heartbeat_json(data_root)
        obj = obj2
        source_path = p2

    # 3) Optional fallback: supervisor state (not physics heartbeat, but “presence”)
    if obj is None:
        sup = Path("/tmp/aion_heartbeat_state.json")
        obj = _read_json(sup)
        source_path = sup if obj else None

    if obj is None or source_path is None:
        return {
            "ok": False,
            "data_root": str(data_root),
            "heartbeat": None,
            "source_path": None,
            "age_ms": None,
            "now_s": time.time(),
        }

    # Determine timestamp
    ts_s = None
    for k in ("timestamp", "ts", "time"):
        v = obj.get(k)
        if isinstance(v, (int, float)):
            ts_s = float(v)
            break

    # Handle ISO timestamps if present (some of your logs use iso)
    if ts_s is None:
        iso = obj.get("last_update") or obj.get("timestamp_iso") or obj.get("time_iso")
        if isinstance(iso, str):
            try:
                import datetime
                ts_s = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
            except Exception:
                ts_s = None

    now_s = time.time()
    age_ms = int((now_s - ts_s) * 1000) if ts_s else None

    return {
        "ok": True,
        "data_root": str(data_root),
        "source_path": str(source_path),
        "age_ms": age_ms,
        "now_s": now_s,
        "heartbeat": obj,
    }