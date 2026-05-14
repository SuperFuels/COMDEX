from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from datetime import datetime
import difflib
import uuid

from backend.modules.dna_chain.dna_registry import register_proposal

router = APIRouter()

class MutationPayload(BaseModel):
    from_container: str
    coord: str
    logic_before: str
    logic_after: str

@router.post("/api/aion/submit-mutation")
async def submit_mutation(payload: MutationPayload, request: Request):
    try:
        diff = "\n".join(
            difflib.unified_diff(
                payload.logic_before.splitlines(),
                payload.logic_after.splitlines(),
                lineterm="",
                fromfile="before",
                tofile="after",
            )
        )

        proposal = {
            "proposal_id": str(uuid.uuid4()),
            "file": f"{payload.from_container}.dc",
            "coord": payload.coord,
            "reason": "Mutation submitted via GlyphMutator interface",
            "replaced_code": payload.logic_before,
            "new_code": payload.logic_after,
            "diff": diff,
            "approved": False,
            "timestamp": datetime.utcnow().isoformat(),
        }

        register_proposal(proposal)
        return {"status": "ok", "proposal_id": proposal["proposal_id"]}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
