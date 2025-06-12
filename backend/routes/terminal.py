# File: backend/routes/terminal.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Dict, Any

from ..database import get_db
from ..utils.terminal import run_query              # your existing LLM+DB glue
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
def terminal_query(req: QueryRequest, db: Session = Depends(get_db)):
    """
    Run an “AI + DB” pipeline for a free-form query.
    Returns both an analysis text and structured visual data.
    """
    term = req.prompt.strip()

    # 1) Fetch matching products from your DB
    prods = db.fetch_products_like(term)  # e.g. returns List[dict]

    # 2) On-chain / deals metrics
    suppliers_count = db.count_suppliers_for(term)
    one_month_ago = datetime.utcnow() - timedelta(days=30)
    monthly_volume = db.sum_deals_volume(term, since=one_month_ago)

    # 3) Pull recent headlines (optional, stubbed)
    try:
        headlines = fetch_headlines(term, limit=3)
    except Exception:
        headlines = []

    # 4) Run your existing LLM+DB chain to get a narrative – but seed it with our stats
    llm_prompt = (
        f"Market overview for “{term}”:\n"
        f"- Price trends (last 30d)\n"
        f"- Active suppliers: {suppliers_count}\n"
        f"- Trading volume last 30d: {monthly_volume} kg\n"
        f"- Key headlines: {headlines}\n\n"
        "Please summarize in concise bullet points."
    )
    try:
        analysis = run_query(llm_prompt, db)["analysisText"]
    except Exception as e:
        raise HTTPException(500, f"LLM pipeline failed: {e}")

    # 5) Build a price‐history chart payload (timestamps + price)
    history = db.get_price_history(term, days=30)
    chart = [ChartPoint(time=int(pt.timestamp()), value=pt.price) for pt in history]

    return QueryResponse(
        analysisText=analysis,
        visualPayload=VisualPayload(products=prods, chartData=chart),
    )