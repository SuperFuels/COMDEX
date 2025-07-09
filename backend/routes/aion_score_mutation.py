# backend/routes/aion_score_mutation.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict

from backend.modules.dna_chain.mutation_scorer import process_and_score_mutation

router = APIRouter()

class ScoreRequest(BaseModel):
    proposal_id: str
    glyph: Dict

@router.post("/api/aion/score-mutation")
async def score_mutation_api(request: ScoreRequest):
    try:
        score = process_and_score_mutation(request.proposal_id, request.glyph)
        return {"status": "ok", "score": score}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))