# backend/api/aion_dashboard.py
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

# Files produced by your bridge + aggregator
LOG = Path("data/analysis/aion_live_dashboard.jsonl")
OUT = Path("data/analysis/aion_live_dashboard.json")

router = APIRouter(prefix="/api/aion/dashboard", tags=["AION Dashboard"])


def _ensure_paths() -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    if not LOG.exists():
        LOG.write_text("", encoding="utf-8")
    OUT.parent.mkdir(parents=True, exist_ok=True)


def _tail_jsonl(path: Path, max_bytes: int = 512_000, max_lines: int = 5000) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        end = f.tell()
        size = min(end, max_bytes)
        f.seek(max(0, end - size))
        chunk = f.read().decode("utf-8", errors="ignore")

    rows: List[Dict[str, Any]] = []
    lines = [ln for ln in chunk.splitlines() if ln.strip()]
    for ln in lines[-max_lines:]:
        try:
            obj = json.loads(ln)
            if isinstance(obj, dict) and obj:
                rows.append(obj)
        except Exception:
            continue
    return rows


def _build_summary_inline(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Minimal inline summary (fast). If you want the full logic, call your aggregator module.
    """
    # Prefer the full aggregator if available
    try:
        from backend.simulations.aion_dashboard_aggregator import build_summary  # type: ignore
        # match your aggregator defaults
        return build_summary(rows, bad_lines=0, recent_n=int(os.getenv("AION_DASH_RECENT_N", "200")))
    except Exception:
        # fallback: just basic counts
        return {
            "generated_at": time.time(),
            "events": len(rows),
            "paths": {"log": str(LOG), "out": str(OUT)},
            "last": rows[-1] if rows else None,
        }


def _compute_and_write_summary() -> Dict[str, Any]:
    _ensure_paths()
    rows = _tail_jsonl(LOG)
    summary = _build_summary_inline(rows)
    OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


@router.get("/health")
def dashboard_health() -> Dict[str, Any]:
    _ensure_paths()
    ok = True
    details = {
        "log_exists": LOG.exists(),
        "out_exists": OUT.exists(),
        "log_path": str(LOG),
        "out_path": str(OUT),
    }
    return {"status": "ok" if ok else "error", "details": details}


@router.get("")
def dashboard_get(refresh: int = Query(0, description="1 = recompute aggregator now")) -> JSONResponse:
    _ensure_paths()
    if refresh == 1 or not OUT.exists():
        summary = _compute_and_write_summary()
        return JSONResponse(summary)

    try:
        return JSONResponse(json.loads(OUT.read_text(encoding="utf-8")))
    except Exception:
        summary = _compute_and_write_summary()
        return JSONResponse(summary)


@router.get("/events")
def dashboard_events(limit: int = Query(200, ge=1, le=5000)) -> Dict[str, Any]:
    _ensure_paths()
    rows = _tail_jsonl(LOG)
    return {"events": rows[-limit:], "count": min(limit, len(rows))}


# WebSocket tail: frontend can subscribe instead of polling
@router.websocket("/ws")  # /api/aion/dashboard/ws
async def dashboard_ws(websocket: WebSocket):
    await websocket.accept()
    _ensure_paths()

    # hello
    await websocket.send_text(json.dumps({"type": "hello", "ts": time.time(), "path": str(LOG)}))

    try:
        with open(LOG, "r", encoding="utf-8") as f:
            f.seek(0, os.SEEK_END)

            while True:
                line = f.readline()
                if not line:
                    await asyncio.sleep(0.5)
                    continue
                s = line.strip()
                if not s:
                    continue
                # pass-through (don’t normalize here)
                await websocket.send_text(s)

    except WebSocketDisconnect:
        return
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"type": "error", "error": str(e)}))
        except Exception:
            pass
        return


# Convenience WS at a nicer path too:
# /ws/aion/dashboard  (no /api prefix)
ws_router = APIRouter(tags=["AION Dashboard WS"])

@ws_router.websocket("/ws/aion/dashboard")
async def dashboard_ws_short(websocket: WebSocket):
    # reuse the same handler
    await dashboard_ws(websocket)