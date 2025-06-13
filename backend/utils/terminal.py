import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

import openai
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.product import Product
from ..models.deal import Deal
from ..utils.news import fetch_headlines

# 1) Configure OpenAI from your env
openai.api_key = os.getenv("OPENAI_API_KEY")


def run_query(prompt: str, db: Session) -> Dict[str, Any]:
    """
    AI + DB integration for your “terminal” endpoint.
    Returns a dict with:
      - analysisText: str
      - visualPayload: { products: list, chartData: list, suppliers: int, volumes: float }
    """
    term = prompt.strip()

    # ─── 1) Product lookup ────────────────────────────────────────
    prods: List[Product] = (
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

    # ─── 2) Price-history (last 30d) ───────────────────────────────
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    history_points = (
        db.query(Deal)
          .filter(Deal.product_title.ilike(f"%{term}%"))
          .filter(Deal.created_at >= thirty_days_ago)
          .order_by(Deal.created_at)
          .all()
    )
    chart_payload = [
        {
          "time": int(d.created_at.timestamp()),
          "value": (d.total_price / d.quantity_kg) if d.quantity_kg else 0
        }
        for d in history_points
    ]

    # ─── 3) Supplier count & volume sum ────────────────────────────
    suppliers_count: int = (
        db.query(Product.owner_id)
          .filter(Product.title.ilike(f"%{term}%"))
          .distinct()
          .count()
    )
    volume_sum: float = (
        db.query(func.sum(Deal.quantity_kg))
          .filter(Deal.product_title.ilike(f"%{term}%"))
          .filter(Deal.created_at >= thirty_days_ago)
          .scalar()
        or 0.0
    )

    # ─── 4) Headlines (optional) ──────────────────────────────────
    try:
        headlines: List[str] = fetch_headlines(term, limit=3)
    except Exception:
        headlines = []

    # ─── 5) LLM call ──────────────────────────────────────────────
    system_msg = (
        "You are a senior commodity market analyst.\n"
        "Provide concise, bullet-point market overviews."
    )
    user_msg = (
        f"Market overview for “{term}”:\n"
        f"- Price points: {len(chart_payload)} in last 30d\n"
        f"- Active suppliers: {suppliers_count}\n"
        f"- Volume 30d: {volume_sum:.0f} kg\n"
        f"- Key headlines: {headlines}\n\n"
        "Summarize as bullet points."
    )
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": user_msg}
            ],
            temperature=0.7,
            max_tokens=300,
        )
        analysis = resp.choices[0].message.content.strip()
    except Exception as e:
        analysis = f"⚠️ LLM error: {e}"

    return {
        "analysisText": analysis,
        "visualPayload": {
            "products": products_payload,
            "chartData": chart_payload,
            "suppliers": suppliers_count,
            "volumes": volume_sum,
        },
    }