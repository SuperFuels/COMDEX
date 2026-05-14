# ===============================
# 📁 backend/api/api_lightcone.py
# ===============================
"""
🔌 LightCone API for SCI AtomSheet / QFC HUD
─────────────────────────────────────────────
- Supports forward/reverse symbolic traces
- Async-safe file loading (aiofiles shim)
- Batch or single entry IDs
- Returns {trace: [...]} for single; {traces: {id: [...]}} for multiple
- Optional QFC broadcast with container_id
- Optional Bearer token (use 'valid_token')
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import logging
import os

# --- aiofiles (optional) -----------------------------------------------------
try:
    import aiofiles  # type: ignore
except Exception:
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

from backend.modules.atomsheets.atomsheet_engine import load_atom
from backend.modules.atomsheets.models import AtomSheet, GlyphCell
from backend.modules.codex.lightcone_tracer import (
    execute_lightcone_forward,
    execute_lightcone_reverse,
)
from backend.modules.visualization.qfc_websocket_bridge import broadcast_qfc_beams
from backend.utils.glyph_schema_validator import validate_atomsheet  # keep your validator

logger = logging.getLogger(__name__)

# Router + optional auth (match atomsheets router style)
router = APIRouter()  # main.py may include this under a global /api prefix
security = HTTPBearer(auto_error=False)

# Default fallback sheet (canonical .atom)
DEFAULT_SHEET_PATH = Path("backend/data/sheets/example_sheet.atom")


def _validate_token(creds: Optional[HTTPAuthorizationCredentials]) -> None:
    """If a bearer token is provided, require it to match 'valid_token'."""
    if creds and creds.credentials != "valid_token":
        raise HTTPException(status_code=401, detail="Invalid token")


async def _load_and_validate_sheet(file_path: Path) -> AtomSheet:
    """
    Async-safe loader: read JSON, validate, then construct AtomSheet via load_atom(dict).
    """
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"AtomSheet not found at {file_path}")

    try:
        async with aiofiles.open(str(file_path), mode="r", encoding="utf-8") as f:  # type: ignore
            raw = await f.read()
        raw_sheet = json.loads(raw)
    except Exception as e:
        logger.exception("Failed to read AtomSheet")
        raise HTTPException(status_code=500, detail=f"Failed to read AtomSheet: {str(e)}")

    # Validate JSON shape (your utility)
    try:
        valid, msg = validate_atomsheet(raw_sheet)
        if not valid:
            raise HTTPException(status_code=400, detail={"sheet_error": msg})
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"AtomSheet validation raised unexpectedly: {e}")

    # Build AtomSheet model (load_atom accepts dicts)
    try:
        sheet: AtomSheet = load_atom(raw_sheet)  # type: ignore
        return sheet
    except Exception as e:
        logger.exception("Failed to construct AtomSheet")
        raise HTTPException(status_code=500, detail=f"Failed to construct AtomSheet: {str(e)}")


@router.get("/lightcone")
async def get_lightcone_trace(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    # Allow either a single entry_id or multiple entry_ids
    entry_id: Optional[str] = Query(None, description="ID of starting GlyphCell"),
    entry_ids: Optional[List[str]] = Query(None, description="IDs of starting GlyphCells"),
    direction: str = Query("forward", description="Trace direction: forward or reverse"),
    file: Optional[str] = Query(None, description="Path to AtomSheet .atom or .sqs.json file"),
    container_id: Optional[str] = Query(None, description="Container ID for QFC correlation"),
    push_to_qfc: bool = Query(True, description="Broadcast trace to QFC WebSocket"),
) -> JSONResponse:
    """
    Compute LightCone traces for one or more entry cells.

    Example:
        GET /api/lightcone?file=backend/data/sheets/example_sheet.atom&entry_id=A1&direction=forward
        Authorization: Bearer valid_token
    """
    _validate_token(credentials)

    # Resolve input sheet path and pre-check for clearer error (load also checks)
    sheet_path = Path(file) if file else DEFAULT_SHEET_PATH
    if file and not os.path.exists(file):
        raise HTTPException(status_code=404, detail=f"File not found: {file}")

    sheet: AtomSheet = await _load_and_validate_sheet(sheet_path)
    cells: List[GlyphCell] = list(sheet.cells.values())  # AtomSheet.cells is a dict

    # Normalize IDs
    ids: List[str] = []
    if entry_id:
        ids.append(entry_id)
    if entry_ids:
        ids.extend([i for i in entry_ids if i])

    if not ids:
        raise HTTPException(status_code=400, detail="At least one of 'entry_id' or 'entry_ids' is required.")

    # Compute traces
    all_traces: Dict[str, List[Dict[str, Any]]] = {}
    try:
        for eid in ids:
            if direction.lower() == "forward":
                trace = execute_lightcone_forward(cells, eid)
            elif direction.lower() == "reverse":
                trace = execute_lightcone_reverse(cells, eid)
            else:
                raise HTTPException(status_code=400, detail="Invalid direction; must be 'forward' or 'reverse'")

            all_traces[eid] = trace

            # Optional QFC broadcast
            if push_to_qfc:
                try:
                    await broadcast_qfc_beams(
                        container_id=container_id or str(sheet_path),
                        payload=[{
                            "type": "lightcone_trace",
                            "entry_id": eid,
                            "trace": trace,
                            "direction": direction
                        }],
                    )
                except Exception as e:
                    logger.warning(f"Failed to broadcast LightCone trace to QFC: {e}")

        # Lightweight metrics, helpful for HUD
        metrics = {
            "direction": direction,
            "entries": ids,
            "trace_lengths": {k: len(v) for k, v in all_traces.items()},
        }

        # Frontend expects {trace: [...]} when single ID
        if len(ids) == 1:
            eid = ids[0]
            return JSONResponse(content={"trace": all_traces[eid], "direction": direction, "metrics": metrics})

        # Otherwise return batch form
        return JSONResponse(content={"traces": all_traces, "direction": direction, "metrics": metrics})

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error processing LightCone trace")
        raise HTTPException(status_code=500, detail=f"Error processing LightCone: {str(e)}")