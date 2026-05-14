from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Body, HTTPException, WebSocket, WebSocketDisconnect

# ✅ Single source of truth for actions + event logging
from backend.modules.aion_dashboard.actions import ask, checkpoint, homeostasis_lock, teach

router = APIRouter(tags=["AION Dashboard"])

# Keep in sync with the bridge
DASHBOARD_LOG_PATH = Path(os.getenv("AION_DASHBOARD_JSONL", "data/analysis/aion_live_dashboard.jsonl"))
SNAPSHOT_PATH = Path(os.getenv("AION_DASHBOARD_SNAPSHOT", "data/analysis/aion_live_dashboard.json"))

# Ensure directory exists (WS + endpoints rely on it)
DASHBOARD_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)

DEFAULT_TAIL_LINES = 200
DEFAULT_POLL_S = 0.25


def _safe_read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _tail_jsonl(path: Path, max_lines: int = DEFAULT_TAIL_LINES) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            end = f.tell()
            size = min(end, 512_000)
            f.seek(max(0, end - size))
            chunk = f.read().decode("utf-8", errors="ignore")
        lines = [ln for ln in chunk.splitlines() if ln.strip()]
        for ln in lines[-max_lines:]:
            try:
                obj = json.loads(ln)
                if isinstance(obj, dict):
                    rows.append(obj)
            except Exception:
                continue
    except Exception:
        return []
    return rows


# ─────────────────────────────────────────────────────────────
# ✅ Dashboard actions (UI buttons) — now real, via actions.py
# ─────────────────────────────────────────────────────────────
@router.post("/api/aion/teach")
def api_aion_teach(term: str = Body(...), level: int = Body(1)) -> Dict[str, Any]:
    t = (term or "").strip()
    if not t:
        raise HTTPException(status_code=400, detail="term is required")
    try:
        out = teach(t, int(level or 1), typ="train", mode="dashboard_api")
        return {"ok": True, "result": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/aion/ask")
def api_aion_ask(question: str = Body(...)) -> Dict[str, Any]:
    q = (question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="question is required")
    try:
        out = ask(q, typ="cli", mode="dashboard_api")
        return {"ok": True, "result": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/aion/checkpoint")
def api_aion_checkpoint(term: str = Body("homeostasis")) -> Dict[str, Any]:
    t = (term or "homeostasis").strip() or "homeostasis"
    try:
        out = checkpoint(t, typ="checkpoint", mode="dashboard_api")
        return {"ok": True, "result": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/aion/homeostasis_lock")
def api_aion_homeostasis_lock(
    threshold: float = Body(0.975),
    window_s: int = Body(300),
    term: str = Body("homeostasis"),
) -> Dict[str, Any]:
    t = (term or "homeostasis").strip() or "homeostasis"
    try:
        out = homeostasis_lock(
            threshold=float(threshold),
            window_s=int(window_s),
            term=t,
            typ="homeostasis_lock",
            mode="dashboard_api",
        )
        return {"ok": True, "result": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
# Existing summary endpoint
# ─────────────────────────────────────────────────────────────
@router.get("/api/aion/dashboard")
def aion_dashboard(limit: int = DEFAULT_TAIL_LINES) -> Dict[str, Any]:
    """
    Summary endpoint for the UI.
    - Prefer snapshot JSON if your aggregator writes it
    - Always include last N events from JSONL so UI has something immediately
    """
    snap = _safe_read_json(SNAPSHOT_PATH)
    events = _tail_jsonl(DASHBOARD_LOG_PATH, max_lines=max(10, min(2000, int(limit))))
    return {
        "schema": "aion_dashboard",
        "schema_ver": 1,
        "snapshot": snap,
        "events": events,
        "paths": {
            "jsonl": str(DASHBOARD_LOG_PATH),
            "snapshot": str(SNAPSHOT_PATH),
        },
    }


# ─────────────────────────────────────────────────────────────
# Existing websocket streamer
# ─────────────────────────────────────────────────────────────
@router.websocket("/api/aion/dashboard/ws")
async def aion_dashboard_ws(ws: WebSocket, poll_s: float = DEFAULT_POLL_S) -> None:
    """
    Streams JSONL events as they are appended.

    Protocol:
      - immediately sends a "hello" frame
      - then streams {"type":"event","data":<jsonl_row>}
      - heartbeats {"type":"ping"} every ~10s if idle
    """
    await ws.accept()
    await ws.send_json(
        {
            "type": "hello",
            "schema": "aion_dashboard_ws",
            "schema_ver": 1,
            "jsonl": str(DASHBOARD_LOG_PATH),
            "poll_s": poll_s,
        }
    )

    # Start at end-of-file (follow mode)
    pos = 0
    try:
        if DASHBOARD_LOG_PATH.exists():
            pos = DASHBOARD_LOG_PATH.stat().st_size
    except Exception:
        pos = 0

    idle_ticks = 0
    ping_every = max(1, int(10 / max(0.05, float(poll_s))))

    try:
        while True:
            # allow client to disconnect cleanly
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=float(poll_s))
                if msg.strip().lower().startswith("tail"):
                    tail = _tail_jsonl(DASHBOARD_LOG_PATH, max_lines=DEFAULT_TAIL_LINES)
                    await ws.send_json({"type": "tail", "data": tail})
            except asyncio.TimeoutError:
                pass

            if not DASHBOARD_LOG_PATH.exists():
                idle_ticks += 1
            else:
                try:
                    sz = DASHBOARD_LOG_PATH.stat().st_size
                    if sz < pos:
                        pos = 0  # truncated/rotated
                    if sz > pos:
                        idle_ticks = 0
                        with open(DASHBOARD_LOG_PATH, "rb") as f:
                            f.seek(pos)
                            data = f.read(sz - pos)
                        pos = sz
                        text = data.decode("utf-8", errors="ignore")
                        for ln in text.splitlines():
                            ln = ln.strip()
                            if not ln:
                                continue
                            try:
                                obj = json.loads(ln)
                            except Exception:
                                continue
                            if isinstance(obj, dict):
                                await ws.send_json({"type": "event", "data": obj})
                    else:
                        idle_ticks += 1
                except Exception:
                    idle_ticks += 1

            if idle_ticks % ping_every == 0:
                await ws.send_json({"type": "ping"})
    except WebSocketDisconnect:
        return