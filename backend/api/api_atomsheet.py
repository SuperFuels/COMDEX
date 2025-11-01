# ===============================
# 📁 backend/api/api_atomsheet.py
# ===============================
"""
🔌 AtomSheet API - Serves symbolic AtomSheet (.atom / .sqs.json) to SCI panel

Features:
- Async file loading (with aiofiles shim)
- Safe base-folder path enforcement
- Execute via AtomSheets engine (QPU stack Ph7-10)
- Optional nested expansion (A5)
- Optional glyph/schema validation
- Optional QFC broadcast payload
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import traceback

# --- aiofiles (optional) -----------------------------------------------------
try:
    import aiofiles  # type: ignore
except Exception:
    # Lightweight compatibility shim so tests don't require aiofiles.
    import asyncio

    class _AsyncFile:
        def __init__(self, path: str, mode: str = "r", **kwargs):
            self.path = path
            self.mode = mode
            self.kwargs = kwargs
            self._f = None

        async def __aenter__(self):
            loop = asyncio.get_running_loop()
            def _open():
                return open(self.path, self.mode, **self.kwargs)
            self._f = await loop.run_in_executor(None, _open)
            return self

        async def __aexit__(self, exc_type, exc, tb):
            if self._f:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._f.close)

        async def read(self):
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._f.read)

        async def write(self, data: str):
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._f.write, data)

    class _AiofilesCompat:
        def open(self, path: str, mode: str = "r", **kwargs):
            return _AsyncFile(path, mode, **kwargs)

    aiofiles = _AiofilesCompat()
# -----------------------------------------------------------------------------

from backend.modules.atomsheets.atomsheet_engine import (
    load_atom,
    execute_sheet,
)
from backend.modules.visualization.qfc_websocket_bridge import broadcast_qfc_beams
from backend.utils.glyph_schema_validator import validate_glyph_cell, validate_atomsheet

router = APIRouter()
security = HTTPBearer()

# Base folder & defaults
BASE_SHEET_DIR = Path("backend/data/sheets").resolve()
DEFAULT_SHEET_PATH = (BASE_SHEET_DIR / "example_sheet.atom").resolve()

# Small utility: normalize to .atom if no extension, but allow legacy .sqs.json
def _normalize_atom_path(p: str) -> Path:
    candidate = Path(p)
    if candidate.suffix in (".atom", ".json"):
        return candidate
    # legacy explicit:
    if str(candidate).endswith(".sqs.json"):
        return candidate
    # default to .atom
    return candidate.with_suffix(".atom")


@router.get("/atomsheet", dependencies=[Depends(security)])
async def get_atomsheet(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    file: Optional[str] = Query(None, description="Path to AtomSheet file (.atom or .sqs.json)"),
    container_id: Optional[str] = Query(None, description="QFC container id for HUD/telemetry"),
    push_to_qfc: bool = Query(False, description="Broadcast executed sheet to QFC WebSocket"),
    expand_nested: bool = Query(False, description="Enable nested AtomSheet expansion (A5)"),
    max_nested_depth: int = Query(1, ge=1, le=4, description="Maximum nested expansion depth"),
) -> JSONResponse:
    # 🛡 Token auth
    if credentials.credentials != "valid_token":
        raise HTTPException(status_code=401, detail="Invalid token")

    # 📂 Safe path resolution
    raw_path = _normalize_atom_path(file) if file else DEFAULT_SHEET_PATH
    try:
        sheet_path = raw_path.resolve()
        # must exist under BASE_SHEET_DIR
        if not sheet_path.is_file() or not sheet_path.is_relative_to(BASE_SHEET_DIR):
            raise HTTPException(status_code=404, detail=f"AtomSheet not found at {sheet_path}")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail=f"Invalid AtomSheet path: {file}")

    # 📖 Load raw JSON for optional schema validation
    try:
        async with aiofiles.open(str(sheet_path), mode="r", encoding="utf-8") as f:
            raw_sheet = json.loads(await f.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load AtomSheet: {e}")

    # ✅ Validate AtomSheet (optional strictness - keep defensive)
    ok_sheet, sheet_msg = validate_atomsheet(raw_sheet)
    if not ok_sheet:
        raise HTTPException(status_code=400, detail={"sheet_error": sheet_msg})

    # 🔧 Execute via AtomSheets engine (QPU stack)
    try:
        # load_atom constructs AtomSheet and registers it internally
        sheet = load_atom(str(sheet_path))
        ctx: Dict[str, Any] = {
            "benchmark_silent": True,  # no noisy WS spam by default from QPU
            "expand_nested": bool(expand_nested),
            "max_nested_depth": int(max_nested_depth),
        }
        # pass container id through to any downstream broadcast hooks
        if container_id:
            ctx["container_id"] = container_id

        results = await execute_sheet(sheet, ctx)  # {cell_id: [...]}
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Sheet execution error: {e}\n{tb}")

    # 🧪 Validate each executed cell & collect payloads
    validated_cells: List[Dict[str, Any]] = []
    validation_errors: List[str] = []

    for cid, _runs in results.items():
        c = sheet.cells[cid]
        # serialize a lean view for UI + validators
        cell_dict = {
            "id": c.id,
            "logic": getattr(c, "logic", ""),
            "position": getattr(c, "position", [0, 0, 0, 0]),
            "emotion": getattr(c, "emotion", "neutral"),
            "sqi_score": float(getattr(c, "sqi_score", 1.0) or 1.0),
            "wave_beams": list(getattr(c, "wave_beams", []) or []),
            # surface nested meta if present so the UI can show "↘ expand"
            "meta": getattr(c, "meta", getattr(c, "_meta", {})) or getattr(c, "__dict__", {}).get("meta") or {},
        }
        is_valid, msg = validate_glyph_cell(cell_dict)
        if is_valid:
            validated_cells.append(cell_dict)
        else:
            validation_errors.append(f"❌ Cell '{cell_dict.get('id', 'unknown')}': {msg}")

    if validation_errors:
        raise HTTPException(status_code=400, detail={"validation_errors": validation_errors})

    # 🌐 Optional QFC broadcast (safe/no-op if bridge handles silently)
    if push_to_qfc:
        try:
            payload = {
                "type": "atomsheet_payload",
                "cells": validated_cells,
                "metadata": {"path": str(sheet_path)},
            }
            await broadcast_qfc_beams(container_id=str(container_id or sheet_path), payload=payload)
        except Exception as e:
            # Fail silently but log
            print(f"❌ Failed to broadcast AtomSheet to QFC: {e}")

    # ✅ Return executed + validated sheet
    return JSONResponse(
        content={
            "cells": validated_cells,
            "metadata": {"path": str(sheet_path)},
        }
    )