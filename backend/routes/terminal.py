from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Any, Dict, List

from database import get_db
from utils.terminal import run_query
 
router = APIRouter(prefix="/terminal", tags=["Terminal"])


class QueryRequest(BaseModel):
    prompt: str = Field(..., example="find me 1 tonne of whey protein from Germany")


class ChartPoint(BaseModel):
    time: int
    value: float


class VisualPayload(BaseModel):
    products:  List[Dict[str, Any]]
    chartData: List[ChartPoint]
    suppliers: int
    volumes:   float


class QueryResponse(BaseModel):
    analysisText:  str
    visualPayload: VisualPayload


@router.post("/query", response_model=QueryResponse)
def terminal_query(req: QueryRequest, db: Session = Depends(get_db)):
    term = req.prompt.strip()
    if not term:
        raise HTTPException(400, "Prompt must not be empty")

    try:
        result = run_query(term, db)
    except Exception as e:
        raise HTTPException(500, f"Terminal pipeline failed: {e}")

    analysis = result.get("analysisText", "")
    vp       = result.get("visualPayload", {})
    products = vp.get("products", [])
    chart    = vp.get("chartData", [])
    suppliers = vp.get("suppliers", 0)
    volumes   = vp.get("volumes", 0.0)

    return QueryResponse(
        analysisText  = analysis,
        visualPayload = VisualPayload(
            products  = products,
            chartData = [ChartPoint(**pt) for pt in chart],
            suppliers = suppliers,
            volumes   = volumes,
        )
    )