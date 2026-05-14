# ===============================
# 📁 backend/api/api_lightcone_qfc.py
# ===============================
"""
🔌 LightCone QFC API
──────────────────────
Serves forward/reverse LightCone traces to QFC WebSocket.
Supports async streaming, batching, and typed FastAPI signatures.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
from pathlib import Path
import json

from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
from backend.modules.symbolic_spreadsheet.engine.symbolic_spreadsheet_engine import SymbolicSpreadsheet, execute_sheet
from backend.modules.visualization.qfc_websocket_bridge import broadcast_qfc_beams
from backend.modules.codex.lightcone_tracer import execute_lightcone_forward, execute_lightcone_reverse
from backend.utils.glyph_schema_validator import validate_atomsheet

router = APIRouter()
security = HTTPBearer()

# Default fallback AtomSheet
DEFAULT_SHEET_PATH = Path("backend/data/sheets/example_sheet.atom")


async def _load_and_validate_sheet(file_path: Path) -> SymbolicSpreadsheet:
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"AtomSheet not found at {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_sheet = json.load(f)

        valid, msg = validate_atomsheet(raw_sheet)
        if not valid:
            raise HTTPException(status_code=400, detail={"sheet_error": msg})

        return SymbolicSpreadsheet.from_dict(raw_sheet)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load AtomSheet: {str(e)}")


@router.get("/api/lightcone_qfc", dependencies=[Depends(security)])
async def get_lightcone_qfc(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    entry_ids: List[str] = Query(..., description="ID(s) of starting GlyphCell(s)"),
    direction: str = Query("forward", description="Trace direction: forward or reverse"),
    file: Optional[str] = Query(None, description="Path to AtomSheet .atom file"),
    push_to_qfc: bool = Query(True, description="Broadcast trace to QFC WebSocket"),
) -> JSONResponse:
    # 🛡️ Token check
    if credentials.credentials != "valid_token":
        raise HTTPException(status_code=401, detail="Invalid token")

    sheet_path = Path(file) if file else DEFAULT_SHEET_PATH
    sheet: SymbolicSpreadsheet = await _load_and_validate_sheet(sheet_path)
    cells: List[GlyphCell] = sheet.cells  # type: ignore

    all_traces: Dict[str, List[Dict[str, Any]]] = {}

    try:
        # Batch over multiple entry IDs
        for entry_id in entry_ids:
            if direction.lower() == "forward":
                trace = execute_lightcone_forward(cells, entry_id)
            elif direction.lower() == "reverse":
                trace = execute_lightcone_reverse(cells, entry_id)
            else:
                raise HTTPException(status_code=400, detail="Invalid direction; must be 'forward' or 'reverse'")

            all_traces[entry_id] = trace

            # Async broadcast to QFC
            if push_to_qfc:
                await broadcast_qfc_beams(
                    container_id=str(sheet_path),
                    payload=[{"entry_id": entry_id, "trace": trace, "direction": direction}]
                )

        return JSONResponse(content={"traces": all_traces, "direction": direction})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing LightCone QFC: {str(e)}")