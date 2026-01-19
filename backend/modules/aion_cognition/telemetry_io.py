# backend/modules/aion_cognition/telemetry_io.py
from __future__ import annotations
import os, json, time
from typing import Any, Dict

def write_qdata(path: str, obj: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = dict(obj)
    payload.setdefault("ts", time.time())
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)