# backend/utils/terminal.py
from sqlalchemy.orm import Session

def run_query(prompt: str, db: Session) -> dict:
    low = prompt.strip().lower()

    # ─── SALES REPORT ───────────────────────
    if low == "sales":
        text = "📊 Here’s your sales summary for the month…"
        # run real DB queries to pull sales figures…
        chart = [{"time":  … }, …]
        return {"analysisText": text, "visualPayload": {"chartData": chart}}

    # ─── SHIPMENTS ──────────────────────────
    if low == "shipments":
        text = "🚚 Your in-flight shipments:"
        rows = db.query(...).all()  # your Shipment model
        suppliers = [r.to_dict() for r in rows]
        return {"analysisText": text, "visualPayload": {"products": suppliers}}

    # ─── PRODUCT MARKET ANALYSIS ───────────
    # e.g. “price of whey protein” or free-form
    # fallback to buyer-style product lookup
    text = f"🔍 Market look-up for “{prompt}”"
    prods = db.query(Product)\
              .filter(Product.title.ilike(f"%{prompt}%"))\
              .limit(10).all()
    chart = [{"time": p.created_at.timestamp(), "value": p.price_per_kg}
             for p in prods]
    return {
      "analysisText": text,
      "visualPayload": {
        "products": [p.to_dict() for p in prods],
        "chartData": chart,
      }
    }