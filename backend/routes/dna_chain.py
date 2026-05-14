# backend/routes/dna_chain.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.modules.dna_chain.dna_writer import approve_dna_proposal
import os

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

router = APIRouter()

class ApproveRequest(BaseModel):
    proposal_id: str
    master_key: str

@router.post("/api/aion/dna/approve")
def approve_dna(req: ApproveRequest):
    correct_key = os.getenv("AION_MASTER_KEY")
    if not correct_key:
        raise HTTPException(status_code=500, detail="Master key not configured.")
    if req.master_key != correct_key:
        raise HTTPException(status_code=403, detail="Invalid master key.")
    
    result = approve_dna_proposal(req.proposal_id)
    if result.get("status") != "applied":
        raise HTTPException(status_code=400, detail="Approval failed.")
    
    return result