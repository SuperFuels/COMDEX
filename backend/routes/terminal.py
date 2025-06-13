# File: backend/routes/terminal.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Any, Dict, List

from ..database import get_db
from ..utils.terminal import run_query

router = APIRouter(prefix="/terminal", tags=["Terminal"])


class QueryRequest(BaseModel):
    prompt: str = Field(..., example="find me 1 tonne of whey protein from Germany")


class ChartPoint(BaseModel):
    time: int
    value: float


class VisualPayload(BaseModel):
    products: List[Dict[str, Any]]
    chartData: List[ChartPoint]


class QueryResponse(BaseModel):
    analysisText: str
    visualPayload: VisualPayload


@router.post("/query", response_model=QueryResponse)
def terminal_query(req: QueryRequest, db: Session = Depends(get_db)):
    """
    Run your full “AI + DB” pipeline via `run_query`.
    Returns the LLM analysis text plus structured visual data.
    """
    term = req.prompt.strip()
    if not term:
        raise HTTPException(400, detail="Prompt cannot be empty")

    try:
        # run_query does all of:
        #  • product lookup     (db.fetch_products_like or direct SQLAlchemy)
        #  • price-history      (last 30d via Deal)
        #  • supplier & volume  (distinct count & sum)
        #  • top headlines      (via fetch_headlines)
        #  • LLM call           (via openai.ChatCompletion)
        result: Dict[str, Any] = run_query(term, db)
    except Exception as e:
        raise HTTPException(500, detail=f"Terminal pipeline failed: {e}")

    analysis = result.get("analysisText", "")
    vp       = result.get("visualPayload", {})

    products  = vp.get("products", [])
    chartData = vp.get("chartData", [])

    # Validate & return
    return QueryResponse(
        analysisText=analysis,
        visualPayload=VisualPayload(
            products=products,
            chartData=[ChartPoint(**pt) for pt in chartData],
        ),
    )