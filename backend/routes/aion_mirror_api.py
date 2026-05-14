# backend/routes/aion_mirror_api.py
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["AION Mirror"])

# Prefer a single JSON snapshot; fallback to JSONL log tail.
MIRROR_JSON = Path(os.getenv("AION_MIRROR_JSON", "data/analysis/aion_mirror.json"))
MIRROR_LOG  = Path(os.getenv("AION_MIRROR_LOG",  "data/analysis/aion_mirror_log.jsonl"))


def _tail_last_jsonl(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            end = f.tell()
            f.seek(max(0, end - 256_000))
            chunk = f.read().decode("utf-8", errors="ignore")

        for ln in reversed([x for x in chunk.splitlines() if x.strip()]):
            try:
                obj = json.loads(ln)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                continue
    except Exception:
        return {}
    return {}


def _read_mirror() -> Dict[str, Any]:
    now = time.time()
    data: Dict[str, Any] = {}

    used_path: Path | None = None

    if MIRROR_JSON.exists():
        used_path = MIRROR_JSON
        try:
            data = json.loads(MIRROR_JSON.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    elif MIRROR_LOG.exists():
        used_path = MIRROR_LOG
        data = _tail_last_jsonl(MIRROR_LOG)

    # Compute age_ms if the payload provides a timestamp/ts (seconds since epoch)
    ts = data.get("timestamp", None)
    if ts is None:
        ts = data.get("ts", None)

    age_ms = None
    try:
        if isinstance(ts, (int, float)):
            age_ms = int(max(0.0, (now - float(ts)) * 1000.0))
    except Exception:
        age_ms = None

    return {
        "ok": True,
        "ts": now,
        "age_ms": age_ms,
        "path": str(used_path) if used_path else None,
        **(data if isinstance(data, dict) else {}),
    }


@router.get("/api/mirror")
def api_mirror() -> JSONResponse:
    return JSONResponse(_read_mirror())