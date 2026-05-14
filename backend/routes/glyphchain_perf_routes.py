# backend/routes/glyphchain_perf_routes.py
from __future__ import annotations

import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/glyphchain/dev", tags=["glyphchain-dev"])

_ARTIFACT_CANDIDATES = [
    Path("backend/tests/artifacts/glyphchain_perf_latest.json"),
    Path("backend/tests/artifacts/chain_sim_perf_latest.json"),  # backward compat
]

@router.get("/perf/latest")
def glyphchain_perf_latest():
    p = next((x for x in _ARTIFACT_CANDIDATES if x.exists()), None)
    if p is None:
        raise HTTPException(status_code=404, detail="perf artifact not found (run pytest perf test first)")

    try:
        data = json.loads(p.read_text())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to read perf artifact: {e}")

    return JSONResponse(content={"ok": True, "artifact_path": str(p), "data": data})