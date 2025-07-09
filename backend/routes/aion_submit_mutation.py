from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import uuid

from backend.modules.dna_chain.dna_registry import register_proposal as store_proposal

router = APIRouter()

class MutationProposal(BaseModel):
    from_container: str
    logic_before: str
    logic_after: str

@router.post("/api/aion/submit-mutation")
async def submit_mutation(proposal: MutationProposal, request: Request):
    try:
        proposal_id = str(uuid.uuid4())
        record = {
            "proposal_id": proposal_id,
            "file": proposal.from_container,
            "reason": f"Mutation submitted via GlyphMutator UI.",
            "replaced_code": proposal.logic_before.strip(),
            "new_code": proposal.logic_after.strip(),
            "diff": generate_diff(proposal.logic_before, proposal.logic_after),
            "approved": False,
        }
        store_proposal(record)
        return {"status": "ok", "proposal_id": proposal_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def generate_diff(before: str, after: str) -> str:
    import difflib
    before_lines = before.strip().splitlines()
    after_lines = after.strip().splitlines()
    diff = difflib.unified_diff(before_lines, after_lines, fromfile='before', tofile='after', lineterm='')
    return "\n".join(diff)