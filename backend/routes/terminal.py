# backend/routes/terminal.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..database import get_db
from ..utils.terminal import run_query

router = APIRouter(
    prefix="/api/terminal",
    tags=["Terminal"],
)

class QueryRequest(BaseModel):
    prompt: str = Field(..., example="find me 1 tonne of whey protein from Germany")

class QueryResponse(BaseModel):
    analysisText: str
    visualPayload: dict

@router.post("/query", response_model=QueryResponse)
def terminal_query(
    req: QueryRequest,
    db: Session = Depends(get_db),
):
    try:
        result = run_query(req.prompt, db)
    except Exception as e:
        raise HTTPException(500, f"Terminal pipeline failed: {e}")
    return QueryResponse(
        analysisText=result["analysisText"],
        visualPayload=result["visualPayload"]
    )