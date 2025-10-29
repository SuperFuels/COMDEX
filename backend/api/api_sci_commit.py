# ============================================================
#  🧠 SCI ↔ Knowledge Graph Integration API
# ============================================================
# Provides commit and verification routes for PhotonLens frames,
# PhotonLang executions, and container memory synchronization.
# ============================================================

from fastapi import APIRouter, HTTPException, Request
from datetime import datetime
import json

router = APIRouter(prefix="/api/sci", tags=["SCI Knowledge Graph"])

# ------------------------------------------------------------
#  Commit Atom / Scroll Snapshot
# ------------------------------------------------------------
@router.post("/commit_atom")
async def commit_atom(request: Request):
    """
    Store a symbolic Atom, Photon frame, or resonance snapshot into
    the Knowledge Graph container. This links it to ResonantMemory
    and allows retrieval by the SCI IDE or Lean verification later.
    """
    body = await request.json()
    label = body.get("label", "unnamed_atom")
    container_id = body.get("container_id", "sci:unknown")
    frame = body.get("frame", {})

    try:
        # Import lightweight memory saver (uses ResonantMemoryCache)
        from backend.modules.resonant_memory.resonant_memory_saver import save_scroll_to_memory

        metadata = {
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "source": "sci_commit_atom",
            "frame_summary": list(frame.keys())[:10],
        }

        save_scroll_to_memory(
            user_id=container_id,
            label=label,
            content=json.dumps(frame, ensure_ascii=False),
            metadata=metadata,
        )

        print(f"[SCI Commit] 💾 Stored Atom '{label}' in container {container_id}")
        return {"ok": True, "label": label, "metadata": metadata}

    except Exception as e:
        print(f"[SCI Commit Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------
#  Verify Atom in Lean Proof System
# ------------------------------------------------------------
@router.post("/lean/verify_atom")
async def verify_atom(request: Request):
    """
    Sends a committed Atom to the Lean verification backend.
    Each Atom is translated to a theorem and validated for resonance coherence.
    """
    body = await request.json()
    atom_label = body.get("label")
    proof_code = body.get("proof", "")
    if not atom_label:
        raise HTTPException(status_code=400, detail="Missing atom label")

    try:
        # Hook into the Lean bridge
        from backend.modules.lean.lean_bridge import verify_lean_atom

        result = await verify_lean_atom(atom_label, proof_code)
        print(f"[LeanVerify] ✅ Atom '{atom_label}' verified")
        return {"ok": True, "result": result}
    except Exception as e:
        print(f"[LeanVerify Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))