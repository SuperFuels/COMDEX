# -*- coding: utf-8 -*-
# ===============================
# 📁 backend/routers/atomsheets.py
# ===============================
from __future__ import annotations

import os
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, List

from fastapi import APIRouter, Query, Body, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from backend.modules.atomsheets.atomsheet_engine import (
    load_atom,
    execute_sheet as engine_execute_sheet,
    to_dc_json as engine_to_dc_json,
)
from backend.modules.patterns.pattern_trace_engine import record_trace
from backend.modules.utils.time_utils import now_utc_ms

# -----------------------
# Optional WS broadcast; safe no-op if unavailable
# -----------------------
def _broadcast(container_id: Optional[str], payload: Dict[str, Any]) -> None:
    """Emit a QFC update if the WebSocket layer is available."""
    if not container_id:
        return
    try:
        from backend.modules.qfc.qfc_socket import broadcast_qfc_update  # type: ignore
        import asyncio

        asyncio.create_task(broadcast_qfc_update(container_id, payload))
    except Exception:
        # Defensive: don’t crash REST if WS layer isn’t loaded
        record_trace("atomsheet", "[WS] Broadcast helper not available")


# -----------------------
# Router + (optional) auth
# -----------------------
router = APIRouter(prefix="/api", tags=["atomsheets"])
security = HTTPBearer(auto_error=False)  # token optional; if present and wrong → 401


# -----------------------
# Pydantic models
# -----------------------
class ExecuteOptions(BaseModel):
    benchmark_silent: Optional[bool] = True
    batch_collapse: Optional[bool] = True
    expand_nested: Optional[bool] = False
    max_nested_depth: Optional[int] = 1
    phase9_enabled: Optional[bool] = False
    phase10_enabled: Optional[bool] = False
    phase10_precision: Optional[str] = "fp8"


class ExecuteRequest(BaseModel):
    file: Optional[str] = None              # path to .atom (or legacy .sqs.json)
    sheet: Optional[Dict[str, Any]] = None  # inline sheet dict
    container_id: Optional[str] = None
    options: Optional[ExecuteOptions] = ExecuteOptions()


class UpsertCellRequest(BaseModel):
    file: str
    id: Optional[str] = None
    logic: str
    position: List[int]  # [x,y,z,t]
    emotion: Optional[str] = "neutral"
    meta: Optional[Dict[str, Any]] = None


# -----------------------
# Helpers
# -----------------------
def _serialize_cell(c: Any) -> Dict[str, Any]:
    """Convert a GlyphCell-like object into a stable JSON-serializable dict."""
    meta = getattr(c, "meta", None)
    if not isinstance(meta, dict):
        meta = {}

    logic_type = getattr(c, "logic_type", None) or meta.get("logic_type")

    d: Dict[str, Any] = {
        "id": getattr(c, "id", ""),
        "logic": getattr(c, "logic", ""),
        "logic_type": logic_type,
        "position": getattr(c, "position", [0, 0, 0, 0]),
        "emotion": getattr(c, "emotion", None),
        # Quality & metrics (E7)
        "sqi_score": getattr(c, "sqi_score", None),
        "entropy": getattr(c, "entropy", None),
        "novelty": getattr(c, "novelty", None),
        "harmony": getattr(c, "harmony", None),
        # Execution state
        "validated": getattr(c, "validated", None),
        "result": getattr(c, "result", None),
        "prediction": getattr(c, "prediction", None),
        # B6: CodexLang server-side preview
        "codex_eval": getattr(c, "codex_eval", None),
        "codex_error": getattr(c, "codex_error", None),
    }

    # Include beams for GHX/HUD rendering
    wb = getattr(c, "wave_beams", None)
    if isinstance(wb, list):
        d["wave_beams"] = wb

    if meta:
        d["meta"] = meta

    return d


def _validate_token(creds: Optional[HTTPAuthorizationCredentials]) -> None:
    """If a bearer token is provided, require it to match 'valid_token'."""
    if creds and creds.credentials != "valid_token":
        raise HTTPException(status_code=401, detail="Invalid token")


# -----------------------
# Routes
# -----------------------
@router.get("/atomsheet")
async def get_atomsheet(
    file: str = Query(..., description="Path to .atom (or legacy .sqs.json)"),
    container_id: Optional[str] = Query(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """Load an AtomSheet and return its JSON (cells included)."""
    _validate_token(credentials)

    if not os.path.exists(file):
        raise HTTPException(status_code=404, detail=f"File not found: {file}")

    try:
        sheet = load_atom(file)
        return {
            "id": sheet.id,
            "title": sheet.title,
            "dims": sheet.dims,
            "cells": [_serialize_cell(c) for c in sheet.cells.values()],
            "meta": sheet.meta,
            "container_id": container_id,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load AtomSheet: {e}") from e


@router.post("/atomsheet/execute")
async def execute_atomsheet(
    req: ExecuteRequest = Body(...),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """Execute an AtomSheet by path or inline dict. Emits WS broadcasts if needed."""
    _validate_token(credentials)

    if not req.file and not req.sheet:
        raise HTTPException(status_code=400, detail="Provide 'file' or 'sheet'")

    try:
        sheet = load_atom(req.file) if req.file else load_atom(req.sheet)  # type: ignore
        ctx = dict((req.options or ExecuteOptions()).model_dump())
        if req.container_id:
            ctx["container_id"] = req.container_id

        start_ms = now_utc_ms()
        results = await engine_execute_sheet(sheet, ctx)
        elapsed_ms = now_utc_ms() - start_ms

        sqi_stats = {cid: float(getattr(c, "sqi_score", 1.0) or 1.0) for cid, c in sheet.cells.items()}

        payload: Dict[str, Any] = {
            "ok": True,
            "sheet_id": sheet.id,
            "beam_counts": {cid: len(v) for cid, v in results.items()},
            "metrics": {
                "execution_time_ms": elapsed_ms,
                "sqi": sqi_stats,
            },
            "cells": [_serialize_cell(c) for c in sheet.cells.values()],
        }

        if req.container_id and not ctx.get("benchmark_silent"):
            _broadcast(
                req.container_id,
                {
                    "type": "atomsheet_executed",
                    "sheet_id": sheet.id,
                    "beam_counts": payload["beam_counts"],
                    "metrics": payload["metrics"],
                },
            )

        return payload
    except HTTPException:
        raise
    except Exception as e:
        record_trace("atomsheet", f"[Execute Error] {e}")
        raise HTTPException(status_code=500, detail=f"Execution failed: {e}") from e


@router.get("/atomsheet/export")
async def export_atomsheet(
    file: str = Query(..., description="Path to .atom (or legacy .sqs.json)"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """Load then export to a `.dc.json`-style snapshot (in-memory)."""
    _validate_token(credentials)

    if not os.path.exists(file):
        raise HTTPException(status_code=404, detail=f"File not found: {file}")

    try:
        sheet = load_atom(file)
        return engine_to_dc_json(sheet)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Export failed: {e}") from e


@router.post("/atomsheet/upsert")
async def upsert_cell(
    req: UpsertCellRequest = Body(...),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """Insert or update a cell, then persist the sheet to disk."""
    _validate_token(credentials)

    try:
        sheet = load_atom(req.file)
        cid = req.id or f"c_{len(sheet.cells)}_{int(time.time() * 1000)}"

        if cid in sheet.cells:
            c = sheet.cells[cid]
            c.logic = req.logic
            c.position = req.position
            if req.emotion is not None:
                c.emotion = req.emotion
            if req.meta:
                for k, v in req.meta.items():
                    try:
                        setattr(c, k, v)
                    except Exception:
                        pass
        else:
            from backend.modules.atomsheets.models import GlyphCell  # safe local import
            c = GlyphCell(
                id=cid,
                logic=req.logic,
                position=req.position,
                emotion=req.emotion or "neutral",
            )
            for k, v in (req.meta or {}).items():
                try:
                    setattr(c, k, v)
                except Exception:
                    pass
            sheet.cells[cid] = c

        p = Path(req.file)
        if not p.suffix:  # allow bare name → .atom
            p = p.with_suffix(".atom")

        data = {
            "id": sheet.id,
            "title": sheet.title,
            "dims": sheet.dims,
            "meta": sheet.meta,
            "cells": [
                {
                    "id": cc.id,
                    "logic": cc.logic,
                    "position": cc.position,
                    "emotion": getattr(cc, "emotion", "neutral"),
                    "meta": getattr(cc, "meta", None),
                }
                for cc in sheet.cells.values()
            ],
        }

        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return {"ok": True, "id": cid}
    except Exception as e:
        record_trace("atomsheet", f"[Upsert Error] {e}")
        raise HTTPException(status_code=400, detail=f"Upsert failed: {e}") from e