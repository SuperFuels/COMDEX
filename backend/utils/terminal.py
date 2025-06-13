import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

import openai
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.product import Product
from ..models.deal import Deal
from ..models.shipment import Shipment
from ..utils.news import fetch_headlines

# configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY", "")


def run_query(prompt: str, db: Session) -> Dict[str, Any]:
    """
    AI + DB integration for your “terminal” endpoint.
    Returns a dict with:
      - analysisText: str
      - visualPayload: {
          products: List[...],
          chartData: List[{"time": int, "value": float}],
          suppliers: int,
          volumes: float
        }
    """
    term = prompt.strip()
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    # ─── 1) PRODUCTS ───────────────────────────────────────────────
    prods = (
        db.query(Product)
          .filter(Product.title.ilike(f"%{term}%"))
          .limit(10)
          .all()
    )
    products_payload = [
        {
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "price_per_kg": p.price_per_kg,
            "origin_country": p.origin_country,
            "image_url": p.image_url,
        }
        for p in prods
    ]

    # ─── 2) PRICE‐HISTORY CHART ───────────────────────────────────
    deals = (
        db.query(Deal)
          .filter(Deal.product_title.ilike(f"%{term}%"))
          .filter(Deal.created_at >= thirty_days_ago)
          .order_by(Deal.created_at)
          .all()
    )
    chart_payload = [
        {"time": int(d.created_at.timestamp()), "value": d.total_price / d.quantity_kg}
        for d in deals
        if d.quantity_kg and d.total_price is not None
    ]

    # ─── 3) SUPPLIERS COUNT & VOLUME ──────────────────────────────
    suppliers_count = (
        db.query(func.count(func.distinct(Product.owner_id)))
          .filter(Product.title.ilike(f"%{term}%"))
          .scalar()
        or 0
    )
    volume_sum = (
        db.query(func.sum(Deal.quantity_kg))
          .filter(Deal.product_title.ilike(f"%{term}%"))
          .filter(Deal.created_at >= thirty_days_ago)
          .scalar()
        or 0
    )

    # ─── 4) TOP‐3 NEWS HEADLINES ─────────────────────────────────
    try:
        headlines = fetch_headlines(term, limit=3)
    except Exception:
        headlines = []

    # ─── 5) LLM MARKET OVERVIEW ─────────────────────────────────
    system_msg = (
        "You are a senior commodity market analyst. "
        "Provide concise bullet‐point summaries."
    )
    user_msg = (
        f"Market overview for “{term}”:\n"
        f"- Price points (last 30d): {len(chart_payload)} entries\n"
        f"- Active suppliers: {suppliers_count}\n"
        f"- Trading volume (30d): {volume_sum:.0f} kg\n"
        f"- Key headlines: {headlines}\n\n"
        "Summarize in clear bullet points."
    )

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system",  "content": system_msg},
                {"role": "user",    "content": user_msg},
            ],
            temperature=0.7,
            max_tokens=300,
        )
        analysis = resp.choices[0].message.content.strip()
    except Exception as e:
        analysis = f"⚠️ LLM generation failed: {e}"

    return {
        "analysisText": analysis,
        "visualPayload": {
            "products": products_payload,
            "chartData": chart_payload,
            "suppliers": suppliers_count,
            "volumes": volume_sum,
        },
    }