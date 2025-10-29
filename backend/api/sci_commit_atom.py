# ============================================================
# 🧠 SCI Commit Atom API (Unified + Lean Bridge)
# ============================================================
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from datetime import datetime
from typing import Any, Dict, Optional
import traceback

from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
from backend.modules.lean.lean_integration import push_to_lean

router = APIRouter(prefix="/api/sci", tags=["SCI Knowledge"])


# ------------------------------------------------------------
# 📦 Input Model
# ------------------------------------------------------------
class CommitAtomIn(BaseModel):
    label: str
    container_id: str
    sqi: float
    waveform: Dict[str, Any]
    user_id: Optional[str] = "default"


# ------------------------------------------------------------
# 🧠 POST /api/sci/commit_atom
# ------------------------------------------------------------
@router.post("/commit_atom")
async def commit_atom(body: CommitAtomIn):
    """
    Commit a high-SQI symbolic or photon state as a Harmonic Atom.

    Example payload:
    {
        "label": "ResonantState_532nm",
        "sqi": 0.972,
        "container_id": "sci:editor:init",
        "waveform": {...},
        "user_id": "default"
    }
    """

    if body.sqi < 0.95:
        raise HTTPException(status_code=400, detail="SQI too low for commit (requires ≥ 0.95)")

    try:
        kg = get_kg_writer()

        # ------------------------------------------------------------
        # 1️⃣ Create Atom Node for Knowledge Graph
        # ------------------------------------------------------------
        atom_id = f"{body.label}@{body.container_id}"
        atom_node = {
            "id": atom_id,
            "label": body.label,
            "domain": "physics_core",
            "kind": "harmonic_atom",
            "sqi": body.sqi,
            "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            "waveform": body.waveform,
            "user_id": body.user_id or "sci",
        }

        kg.inject_node(body.container_id, atom_node)
        kg.inject_glyph(
            content=f"HarmonicAtom:{body.label}",
            glyph_type="harmonic_atom",
            metadata=atom_node,
            plugin="SCI",
            tags=["harmonics", "auto_commit"]
        )

        # ------------------------------------------------------------
        # 2️⃣ Push to Lean (Formal Proof Stub)
        # ------------------------------------------------------------
        lean_ref = push_to_lean({
            "ref": atom_node["id"],
            "sqi": body.sqi,
            "timestamp": atom_node["timestamp"],
        })

        print(f"[CommitAtom] ✅ Committed → KG + Lean ({lean_ref})")

        return {
            "ok": True,
            "atom_ref": atom_node,
            "lean_path": lean_ref,
            "timestamp": atom_node["timestamp"],
        }

    except Exception as e:
        err = traceback.format_exc()
        print(f"[CommitAtom] ❌ Error committing atom: {e}\n{err}")
        raise HTTPException(status_code=500, detail=f"Commit failed: {e}")