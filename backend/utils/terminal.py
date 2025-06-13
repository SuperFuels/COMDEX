# backend/utils/terminal.py

import os
from datetime import datetime, timedelta
from typing import Dict, Any, List

import openai
from sqlalchemy.orm import Session

from ..models.product import Product
from ..models.shipment import Shipment  # assume you have a Shipment model
from ..models.deal import Deal            # for volumes
from ..utils.news import fetch_headlines

# configure OpenAI once
openai.api_key = os.getenv("OPENAI_API_KEY")


def run_query(prompt: str, db: Session) -> Dict[str, Any]:
    """
    AI + DB integration for your “terminal” endpoint.
    Returns a dict with:
      - analysisText: str
      - visualPayload: { products: list, chartData: list, suppliers: list, volumes: list }
    """
    term = prompt.strip()

    # ─── 1) Fetch matching products ─────────────────────────────
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

    # ─── 2) Build price‐history chart (last 30 days) ───────────
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    history_points = (
        db.query(Deal)  # assume Deal.timestamp + price_per_kg fields
          .filter(Deal.product_title.ilike(f"%{term}%"))
          .filter(Deal.created_at >= thirty_days_ago)
          .order_by(Deal.created_at)
          .all()
    )
    chart_payload = [
        {"time": int(d.created_at.timestamp()), "value": d.total_price / d.quantity_kg}
        for d in history_points
    ]

    # ─── 3) Compute supplier count & monthly volume ─────────────
    suppliers_count = (
        db.query(Product.owner_id)  # or however you relate supplier
          .filter(Product.title.ilike(f"%{term}%"))
          .distinct()
          .count()
    )
    volume_sum = (
        db.query(Deal)
          .filter(Deal.product_title.ilike(f"%{term}%"))
          .filter(Deal.created_at >= thirty_days_ago)
          .with_entities(func.sum(Deal.quantity_kg))
          .scalar() or 0
    )

    # ─── 4) Fetch top‐3 headlines ───────────────────────────────
    try:
        headlines = fetch_headlines(term, limit=3)
    except Exception:
        headlines = []

    # ─── 5) Ask the LLM for a market overview ───────────────────
    llm_system = "You are a senior commodity market analyst. " \
                 "Provide concise bullet‐point summaries."
    llm_user = (
        f"Market overview for “{term}”:\n"
        f"- Price history over last 30 days: {len(chart_payload)} points\n"
        f"- Active suppliers: {suppliers_count}\n"
        f"- Trading volume last 30 days: {volume_sum:.0f} kg\n"
        f"- Key headlines: {headlines}\n\n"
        "Please summarize in clear bullet points."
    )
    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": llm_system},
                {"role": "user",   "content": llm_user}
            ],
            temperature=0.7,
            max_tokens=300,
        )
        analysis = completion.choices[0].message.content.strip()
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