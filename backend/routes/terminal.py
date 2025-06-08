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
    """
    Run an “AI + DB” pipeline for a free-form query.
    POST /api/terminal/query
    Body: { prompt: "..." }
    """
    try:
        return run_query(req.prompt, db)
    except Exception as e:
        # surface any errors as a 500
        raise HTTPException(500, f"Terminal error: {e}")