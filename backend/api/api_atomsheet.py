# File: backend/api/api_atomsheet.py
# 🔌 Serves symbolic AtomSheet .sqs.json data to the frontend SCI panel

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse

from backend.modules.symbolic_spreadsheet.engine.symbolic_spreadsheet_engine import SymbolicSpreadsheet
from backend.utils.glyph_schema_validator import validate_glyph_cell, validate_atomsheet

from typing import Optional
from pathlib import Path
import json
import os

router = APIRouter()
security = HTTPBearer()

# Default fallback path
DEFAULT_SHEET_PATH = Path("backend/data/sheets/example_sheet.sqs.json")

@router.get("/api/atomsheet", dependencies=[Depends(security)])
def get_atomsheet(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    file: Optional[str] = Query(None)
):
    # 🛡️ Basic token auth (replace with secure auth in production)
    if credentials.credentials != "valid_token":
        raise HTTPException(status_code=401, detail="Invalid token")

    # 📂 Determine file path
    sheet_path = Path(file) if file else DEFAULT_SHEET_PATH
    if not sheet_path.exists():
        raise HTTPException(status_code=404, detail=f"AtomSheet not found at {sheet_path}")

    try:
        with open(sheet_path) as f:
            raw_sheet = json.load(f)

        # ✅ Validate full .sqs.json AtomSheet before execution
        valid_sheet, sheet_msg = validate_atomsheet(raw_sheet)
        if not valid_sheet:
            raise HTTPException(status_code=400, detail={"sheet_error": sheet_msg})

        # ✅ Load + Execute now that it's valid
        sheet = SymbolicSpreadsheet.from_dict(raw_sheet)
        executed_sheet = sheet.execute_sheet()

        validated_cells = []
        errors = []

        for cell in executed_sheet:
            cell_dict = cell.to_dict()
            is_valid, msg = validate_glyph_cell(cell_dict)
            if is_valid:
                validated_cells.append(cell_dict)
            else:
                errors.append(f"❌ Cell '{cell_dict.get('id', 'unknown')}': {msg}")

        if errors:
            raise HTTPException(status_code=400, detail={"validation_errors": errors})

        return JSONResponse(
            content={
                "cells": validated_cells,
                "metadata": sheet.metadata
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"⚠️ Error processing AtomSheet: {str(e)}")