# ===============================
# 📁 backend/api/api_atomsheet.py
# ===============================
"""
🔌 AtomSheet API – Serves symbolic AtomSheet (.sqs.json) to SCI panel

Features:
- Async file loading & execution
- Per-cell validation with glyph schema
- Optional live QFC broadcast
- Safe folder path enforcement
- Phase 7 ready for SymbolicSpreadsheet, SQI, and mutation integration
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import aiofiles
import traceback

from backend.modules.symbolic_spreadsheet.engine.symbolic_spreadsheet_engine import SymbolicSpreadsheet
from backend.modules.visualization.qfc_websocket_bridge import broadcast_qfc_beams
from backend.utils.glyph_schema_validator import validate_glyph_cell, validate_atomsheet

router = APIRouter()
security = HTTPBearer()

# Default fallback path
BASE_SHEET_DIR = Path("backend/data/sheets")
DEFAULT_SHEET_PATH = BASE_SHEET_DIR / "example_sheet.sqs.json"


@router.get("/atomsheet", dependencies=[Depends(security)])
async def get_atomsheet(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    file: Optional[str] = Query(None, description="Path to AtomSheet file"),
    push_to_qfc: bool = Query(False, description="Broadcast sheet to QFC WebSocket")
) -> JSONResponse:
    # 🛡 Token auth
    if credentials.credentials != "valid_token":
        raise HTTPException(status_code=401, detail="Invalid token")

    # 📂 Safe path resolution
    sheet_path = Path(file) if file else DEFAULT_SHEET_PATH
    try:
        sheet_path = sheet_path.resolve()
        if not sheet_path.is_file() or not sheet_path.is_relative_to(BASE_SHEET_DIR.resolve()):
            raise HTTPException(status_code=404, detail=f"AtomSheet not found at {sheet_path}")
    except Exception:
        raise HTTPException(status_code=404, detail=f"Invalid AtomSheet path: {file}")

    # 📖 Load sheet asynchronously
    try:
        async with aiofiles.open(sheet_path, mode="r", encoding="utf-8") as f:
            raw_sheet = json.loads(await f.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load AtomSheet: {e}")

    # ✅ Validate AtomSheet
    valid_sheet, sheet_msg = validate_atomsheet(raw_sheet)
    if not valid_sheet:
        raise HTTPException(status_code=400, detail={"sheet_error": sheet_msg})

    # 🔧 Instantiate SymbolicSpreadsheet and execute sheet
    try:
        sheet: SymbolicSpreadsheet = SymbolicSpreadsheet.from_dict(raw_sheet)
        executed_cells = sheet.execute_sheet()
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Sheet execution error: {e}\n{tb}")

    # 🧪 Validate each cell and collect errors
    validated_cells: List[Dict[str, Any]] = []
    validation_errors: List[str] = []

    for cell in executed_cells:
        cell_dict = cell.to_dict()
        is_valid, msg = validate_glyph_cell(cell_dict)
        if is_valid:
            validated_cells.append(cell_dict)
        else:
            validation_errors.append(f"❌ Cell '{cell_dict.get('id', 'unknown')}': {msg}")

    if validation_errors:
        raise HTTPException(status_code=400, detail={"validation_errors": validation_errors})

    # 🌐 Optional QFC broadcast
    if push_to_qfc:
        try:
            payload = {"cells": validated_cells, "metadata": sheet.metadata}
            await broadcast_qfc_beams(container_id=str(sheet_path), payload=payload)
        except Exception as e:
            # Fail silently but log
            print(f"❌ Failed to broadcast AtomSheet to QFC: {e}")

    # ✅ Return executed + validated sheet
    return JSONResponse(
        content={
            "cells": validated_cells,
            "metadata": sheet.metadata
        }
    )