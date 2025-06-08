# backend/utils/terminal.py

from sqlalchemy.orm import Session
from datetime import datetime, timedelta

# adjust these imports to your real model locations
from .models.product import Product  
# from .models.shipment import Shipment  

def run_query(prompt: str, db: Session) -> dict:
    """
    Maps a simple text prompt into:
      - a sales chart if prompt == "sales"
      - a shipments list if prompt == "shipments"
      - otherwise a product lookup + price history
    """
    low = prompt.strip().lower()

    # ─── SALES REPORT ───────────────────────
    if low == "sales":
        text = "📊 Here’s your sales summary for the past 30 days…"
        # example: build a fake 30-day time series chart
        now = datetime.utcnow()
        chart = []
        for i in range(30):
            day = now - timedelta(days=29 - i)
            # stub: randomish values; replace with real DB query
            chart.append({
                "time": int(day.timestamp()),
                "value": float(1000 + i * 10)
            })
        return {
            "analysisText": text,
            "visualPayload": {"chartData": chart}
        }

    # ─── SHIPMENTS ──────────────────────────
    if low == "shipments":
        text = "🚚 Here are your in-flight shipments:"
        # stub: replace with real Shipment model query
        # rows = db.query(Shipment).filter_by(status="in_transit").all()
        rows = []  # placeholder list
        shipments = []
        for r in rows:
            shipments.append({
                "id": r.id,
                "eta": r.eta.isoformat(),
                "origin": r.origin,
                "destination": r.destination,
                # …any other fields…
            })
        return {
            "analysisText": text,
            "visualPayload": {"products": shipments}
        }

    # ─── PRODUCT MARKET ANALYSIS ───────────
    # fallback: look up by title matching prompt
    text = f"🔍 Market lookup for “{prompt}”"
    prods = (
        db.query(Product)
        .filter(Product.title.ilike(f"%{prompt}%"))
        .limit(10)
        .all()
    )
    chart = [
        {"time": int(p.created_at.timestamp()), "value": p.price_per_kg}
        for p in prods
    ]
    products = []
    for p in prods:
        products.append({
            "id": p.id,
            "title": p.title,
            "description": p.description or "",
            "price_per_kg": p.price_per_kg,
            "origin_country": p.origin_country or "",
            "image_url": p.image_url or ""
        })
    return {
        "analysisText": text,
        "visualPayload": {
            "products": products,
            "chartData": chart,
        },
    }