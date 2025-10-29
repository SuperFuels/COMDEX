# ============================================================
# 🧩 SCI Proof Link Sync API
# ============================================================
from fastapi import APIRouter, HTTPException
from datetime import datetime
import logging

from backend.modules.lean.lean_prover_bridge import sync_all_lean_proofs

router = APIRouter(prefix="/api/sci", tags=["Lean Proofs"])

@router.post("/sync_proof_links")
async def sync_proof_links(limit: int = 0):
    """
    Synchronize all .lean proof files under data/lean/atoms/ with
    their corresponding Harmonic Atoms in the Knowledge Graph.

    Args:
        limit: (optional) placeholder for future pagination or filtering.

    Returns:
        {
            "ok": True,
            "linked": <count>,
            "timestamp": ...
        }
    """
    try:
        logging.info("[SCI] 🔁 Starting Lean↔KG proof link sync...")
        count = sync_all_lean_proofs()

        return {
            "ok": True,
            "linked": count,
            "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
        }

    except Exception as e:
        logging.error(f"[SCI] ❌ Proof link sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))