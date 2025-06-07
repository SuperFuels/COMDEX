from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..utils.terminal import run_query

router = APIRouter(
    prefix="/api/terminal",
    tags=["Terminal"],
)

class QueryRequest(BaseModel):
    prompt: str = Field(..., example="whey protein")

class QueryResponse(BaseModel):
    analysisText: str
    visualPayload: dict

@router.post("/query", response_model=QueryResponse)
def terminal_query(
    req: QueryRequest,
    db: Session = Depends(get_db),
):
    """
    POST /api/terminal/query
    Body: { prompt: "..." }
    """
    result = run_query(req.prompt, db)
    return QueryResponse(**result)