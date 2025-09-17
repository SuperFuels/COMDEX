# File: backend/api/api_lightcone.py
# 🔌 Serves LightCone traces (forward/reverse) for SCI AtomSheet or QFC HUD

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse

from pathlib import Path
from typing import Optional
import json

from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
from backend.modules.symbolic_spreadsheet.engine.symbolic_spreadsheet_engine import SymbolicSpreadsheet
from backend.modules.codex.lightcone_tracer import execute_lightcone_forward, execute_lightcone_reverse
from backend.modules.visualization.qfc_websocket_bridge import broadcast_qfc_update
from backend.utils.glyph_schema_validator import validate_atomsheet

router = APIRouter()
security = HTTPBearer()

# Default fallback sheet
DEFAULT_SHEET_PATH = Path("backend/data/sheets/example_sheet.sqs.json")


@router.get("/api/lightcone", dependencies=[Depends(security)])
async def get_lightcone_trace(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    entry_id: str = Query(..., description="ID of starting GlyphCell"),
    direction: str = Query("forward", description="Trace direction: forward or reverse"),
    file: Optional[str] = Query(None, description="Path to AtomSheet .sqs.json file"),
    push_to_qfc: bool = Query(False, description="Whether to broadcast trace to QFC WebSocket")
):
    # 🛡️ Token check
    if credentials.credentials != "valid_token":
        raise HTTPException(status_code=401, detail="Invalid token")

    sheet_path = Path(file) if file else DEFAULT_SHEET_PATH
    if not sheet_path.exists():
        raise HTTPException(status_code=404, detail=f"AtomSheet not found at {sheet_path}")

    try:
        # 📂 Load sheet
        with open(sheet_path) as f:
            raw_sheet = json.load(f)

        # ✅ Validate AtomSheet
        valid, msg = validate_atomsheet(raw_sheet)
        if not valid:
            raise HTTPException(status_code=400, detail={"sheet_error": msg})

        sheet = SymbolicSpreadsheet.from_dict(raw_sheet)
        cells: list[GlyphCell] = sheet.cells  # type: ignore

        # 🔭 Run LightCone trace
        if direction.lower() == "forward":
            trace = execute_lightcone_forward(cells, entry_id)
        elif direction.lower() == "reverse":
            trace = execute_lightcone_reverse(cells, entry_id)
        else:
            raise HTTPException(status_code=400, detail="Invalid direction; must be 'forward' or 'reverse'")

        # 🌐 Optionally push to QFC WebSocket
        if push_to_qfc:
            try:
                payload = {"trace": trace, "entry_id": entry_id, "direction": direction}
                await broadcast_qfc_update(str(sheet_path), payload)
            except Exception as e:
                print(f"❌ Failed to push LightCone trace to QFC: {e}")

        return JSONResponse(content={"trace": trace, "entry_id": entry_id, "direction": direction})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"⚠️ Error processing LightCone: {str(e)}")