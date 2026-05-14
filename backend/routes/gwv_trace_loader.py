# File: backend/routes/gwv_trace_loader.py

from fastapi import APIRouter, Query
from pathlib import Path
import json

router = APIRouter()

@router.get("/api/gwv_trace")
def get_gwv_trace(container_id: str = Query(...)):
    gwv_path = Path(f"backend/data/gwv_snapshots/{container_id}.gwv")
    if not gwv_path.exists():
        return {"entries": []}
    try:
        with open(gwv_path, "r", encoding="utf-8") as f:
            raw_lines = f.readlines()
        entries = [json.loads(line.strip()) for line in raw_lines if line.strip()]
        return {"entries": entries}
    except Exception as e:
        return {"error": str(e), "entries": []}