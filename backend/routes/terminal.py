# File: backend/routes/terminal.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Dict, Any

from ..database import get_db
from ..utils.terminal import run_query              # your LLM+DB glue
from ..utils.news import fetch_headlines             # optional RSS/news wrapper

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
def terminal_query(
    req: QueryRequest,
    db: Session = Depends(get_db),
):
    """
    Run an “AI + DB” pipeline for a free-form query.
    Returns both an analysis text and structured visual data.
    """
    term = req.prompt.strip()

    # ─── 1) Fetch matching products
    try:
        prods: List[Dict[str, Any]] = db.fetch_products_like(term)
    except Exception as e:
        raise HTTPException(500, detail=f"DB lookup failed: {e}")

    # ─── 2) Compute on-chain / deal metrics
    try:
        suppliers_count: int = db.count_suppliers_for(term)
        one_month_ago = datetime.utcnow() - timedelta(days=30)
        monthly_volume: float = db.sum_deals_volume(term, since=one_month_ago)
    except Exception as e:
        raise HTTPException(500, detail=f"Metrics calculation failed: {e}")

    # ─── 3) Pull top-3 headlines (optional)
    try:
        headlines: List[str] = fetch_headlines(term, limit=3)
    except Exception:
        headlines = []

    # ─── 4) Build LLM prompt and run chain
    llm_prompt = (
        f"Market overview for “{term}”:\n"
        f"- Price trends (last 30d)\n"
        f"- Active suppliers: {suppliers_count}\n"
        f"- Trading volume last 30d: {monthly_volume} kg\n"
        f"- Key headlines: {headlines}\n\n"
        "Please summarize in concise bullet points."
    )
    try:
        # assume run_query returns a dict with "analysisText" + optional visuals
        llm_result = run_query(llm_prompt, db)
        analysis: str = llm_result.get("analysisText", "").strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM pipeline failed: {e}")

    # ─── 5) Build price-history chart payload
    try:
        history = db.get_price_history(term, days=30)
        chart = [
            ChartPoint(time=int(pt.timestamp()), value=pt.price)
            for pt in history
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Price history fetch failed: {e}")

    return QueryResponse(
        analysisText=analysis,
        visualPayload=VisualPayload(products=prods, chartData=chart),
    )