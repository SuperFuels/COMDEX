# backend/utils/terminal.py

from sqlalchemy.orm import Session
from datetime import datetime
from ..models.product import Product
from ..models.user import User

def run_query(prompt: str, db: Session) -> dict:
    """
    AI + DB stub.  Replace the sections marked “TODO” with your OpenAI logic
    and real SQLAlchemy queries.
    Must return a dict with keys:
      - analysisText: str
      - visualPayload: { products: list, chartData: list, suppliers?: list }
    """
    low = prompt.strip().lower()

    # ─── SALES REPORT ───────────────────────
    if low == "sales":
        analysis = "📊 Here’s your sales summary for today…"
        # TODO: real DB aggregation for today’s sales
        chartData = [
            {"time": datetime.utcnow().timestamp(), "value": 100},
            {"time": datetime.utcnow().timestamp() - 3600, "value": 120},
        ]
        return {
            "analysisText": analysis,
            "visualPayload": { "chartData": chartData }
        }

    # ─── SHIPMENTS ──────────────────────────
    if low == "shipments":
        analysis = "🚚 Your in‐flight shipments:"
        # TODO: swap in your Shipment model
        shipments = []  # e.g. db.query(Shipment).all()
        suppliers = [s.__dict__ for s in shipments]
        return {
            "analysisText": analysis,
            "visualPayload": { "products": suppliers }
        }

    # ─── PRODUCT MARKET ANALYSIS ───────────
    # fallback to product lookup by title
    analysis = f"🔍 Market look-up for “{prompt}”"
    prods = (
        db.query(Product)
          .filter(Product.title.ilike(f"%{prompt}%"))
          .limit(10)
          .all()
    )
    chartData = [
        {"time": p.created_at.timestamp(), "value": p.price_per_kg}
        for p in prods
    ]
    return {
        "analysisText": analysis,
        "visualPayload": {
            "products": [
                {
                  "id": p.id,
                  "title": p.title,
                  "description": p.description,
                  "price_per_kg": p.price_per_kg,
                  "origin_country": p.origin_country,
                  "image_url": p.image_url,
                }
                for p in prods
            ],
            "chartData": chartData,
        }
    }