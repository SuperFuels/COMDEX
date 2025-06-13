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
    suppliers: int
    volumes: float


class QueryResponse(BaseModel):
    analysisText: str
    visualPayload: VisualPayload


@router.post("/query", response_model=QueryResponse)
def terminal_query(
    req: QueryRequest,
    db: Session = Depends(get_db),
):
    """
    Run an “AI + DB” pipeline for a free-form query.
    Returns analysisText and structured visual data.
    """
    try:
        result = run_query(req.prompt, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Terminal pipeline failed: {e}")

    # Ensure it matches our Pydantic model
    return QueryResponse(
        analysisText=result["analysisText"],
        visualPayload=VisualPayload(
            products=result["visualPayload"].get("products", []),
            chartData=[
                ChartPoint(**pt) for pt in result["visualPayload"].get("chartData", [])
            ],
            suppliers=result["visualPayload"].get("suppliers", 0),
            volumes=result["visualPayload"].get("volumes", 0.0),
        ),
    )