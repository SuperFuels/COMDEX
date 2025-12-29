from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.modules.lean.lean_proofverifier import verify_snapshot_params

REPO = Path("/workspaces/COMDEX")
LED  = REPO / "data/ledger/lean_snapshots.jsonl"

router = APIRouter(prefix="/api/lean", tags=["Lean"])


class SnapshotVerifyIn(BaseModel):
    steps: int = Field(1024, ge=1)
    dt_ms: int = Field(16, ge=1)
    spec_version: str = Field("v1")


@router.post("/snapshot_verify")
def api_snapshot_verify(payload: SnapshotVerifyIn) -> Dict[str, Any]:
    cert = verify_snapshot_params(payload.steps, payload.dt_ms, payload.spec_version)
    return cert


@router.get("/snapshot/{proof_hash_short}")
def api_snapshot_lookup(proof_hash_short: str) -> Dict[str, Any]:
    if not LED.exists():
        raise HTTPException(status_code=404, detail="ledger not found")

    found: Optional[Dict[str, Any]] = None
    # simple scan (OK for MVP)
    with LED.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = __import__("json").loads(line)
            except Exception:
                continue
            if obj.get("proof_hash_short") == proof_hash_short:
                found = obj

    if not found:
        raise HTTPException(status_code=404, detail="snapshot not found")

    return found