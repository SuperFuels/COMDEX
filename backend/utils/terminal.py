# utils/terminal.py

import os
from datetime import datetime, timedelta
from typing import Dict, Any, List

import openai
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.product import Product
from backend.models.shipment import Shipment
from backend.models.deal import Deal
from backend.utils.news import fetch_headlines

openai.api_key = os.getenv("OPENAI_API_KEY")


def run_query(prompt: str, db: Session) -> Dict[str, Any]:
    """
    AI + DB integration for your “terminal” endpoint.
    Returns a dict with:
      - analysisText: str
      - visualPayload: { products, chartData, suppliers, volumes }
    """
    term = prompt.strip()

    # 1) Fetch matching products
    prods: List[Product] = (
        db.query(Product)
          .filter(Product.title.ilike(f"%{term}%"))
          .limit(10)
          .all()
    )
    products_payload = [
        {
            "id":             p.id,
            "title":          p.title,
            "description":    p.description,
            "price_per_kg":   p.price_per_kg,
            "origin_country": p.origin_country,
            "image_url":      p.image_url,
        }
        for p in prods
    ]

    # 2) Build price‐history chart (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    # join Deal → Product so we can filter on Product.title instead of a missing Deal.product_title
    deals: List[Deal] = (
        db.query(Deal)
          .join(Product, Deal.product_id == Product.id)
          .filter(Product.title.ilike(f"%{term}%"))
          .filter(Deal.created_at >= thirty_days_ago)
          .order_by(Deal.created_at)
          .all()
    )
    chart_payload = [
        {
            "time":  int(d.created_at.timestamp()),
            "value": d.total_price / d.quantity_kg
        }
        for d in deals
    ]

    # 3) Compute active suppliers & volume (same join trick)
    suppliers_count = (
        db.query(Product.owner_id)
          .filter(Product.title.ilike(f"%{term}%"))
          .distinct()
          .count()
    )
    volumes_sum = (
        db.query(func.sum(Deal.quantity_kg))
          .join(Product, Deal.product_id == Product.id)
          .filter(Product.title.ilike(f"%{term}%"))
          .filter(Deal.created_at >= thirty_days_ago)
          .scalar()
        or 0
    )

    # 4) Fetch top-3 headlines
    try:
        headlines = fetch_headlines(term, limit=3)
    except Exception:
        headlines = []

    # 5) Call the LLM
    system_prompt = (
        "You are a senior commodity market analyst. "
        "Provide concise bullet-point summaries."
    )
    user_prompt = (
        f"Market overview for “{term}”:\n"
        f"- {len(chart_payload)} points over last 30d\n"
        f"- Active suppliers: {suppliers_count}\n"
        f"- Volume last 30d: {volumes_sum:.0f} kg\n"
        f"- Headlines: {headlines}\n\n"
        "Summarize in clear bullet points."
    )

    try:
        resp = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system",  "content": system_prompt},
                {"role": "user",    "content": user_prompt},
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
            "products":  products_payload,
            "chartData": chart_payload,
            "suppliers": suppliers_count,
            "volumes":   volumes_sum,
        },
    }