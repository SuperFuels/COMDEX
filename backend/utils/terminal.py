# utils/terminal.py

import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import openai
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.product import Product
from backend.models.shipment import Shipment  # noqa: F401 (import kept for future use)
from backend.models.deal import Deal
from backend.utils.news import fetch_headlines

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH

DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Backward/forward compatible chat completion helper (supports old & new SDKs)
def _chat_completion(messages: List[Dict[str, str]], *, temperature: float = 0.7, max_tokens: int = 300):
    """
    Try the modern client first; gracefully fall back to legacy call paths.
    """
    try:
        # New-style client
        from openai import OpenAI  # type: ignore
        client = OpenAI(api_key=OPENAI_API_KEY)
        return client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception:
        # Legacy global module interfaces
        if OPENAI_API_KEY:
            openai.api_key = OPENAI_API_KEY
        # Try v1 namespaced
        if hasattr(openai, "chat") and hasattr(openai.chat, "completions"):
            return openai.chat.completions.create(  # type: ignore[attr-defined]
                model=OPENAI_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        # Try pre-v1
        if hasattr(openai, "ChatCompletion"):
            return openai.ChatCompletion.create(  # type: ignore[attr-defined]
                model=OPENAI_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        # If all fail, raise the original issue
        raise


def _choice_content(resp) -> str:
    """
    Normalize content extraction for both legacy and new SDK response shapes.
    """
    try:
        choice = resp.choices[0]
    except Exception:
        return "⚠️ LLM response format unexpected."

    # New SDK: choice.message.content
    content = getattr(getattr(choice, "message", None), "content", None)
    if isinstance(content, str):
        return content.strip()

    # Legacy dict style: choice['message']['content']
    try:
        return str(choice["message"]["content"]).strip()
    except Exception:
        return "⚠️ No content in LLM response."


def _safe_unit_price(total_price: Optional[float], qty: Optional[float]) -> Optional[float]:
    try:
        if total_price is None or qty is None or qty == 0:
            return None
        return float(total_price) / float(qty)
    except Exception:
        return None


def run_query(prompt: str, db: Session) -> Dict[str, Any]:
    """
    AI + DB integration for your 'terminal' endpoint.

    Returns:
      {
        "analysisText": str,
        "visualPayload": {
          "products":  [...],
          "chartData": [...],
          "suppliers": int,
          "volumes":   float
        }
      }
    """
    term = (prompt or "").strip()

    # 1) Fetch matching products
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

    # 2) Build price‐history chart (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    deals: List[Deal] = (
        db.query(Deal)
        .join(Product, Deal.product_id == Product.id)
        .filter(Product.title.ilike(f"%{term}%"))
        .filter(Deal.created_at >= thirty_days_ago)
        .order_by(Deal.created_at)
        .all()
    )
    chart_payload = []
    for d in deals:
        unit = _safe_unit_price(getattr(d, "total_price", None), getattr(d, "quantity_kg", None))
        if unit is None:
            continue
        ts = int(getattr(d, "created_at").timestamp()) if getattr(d, "created_at", None) else None
        if ts is None:
            continue
        chart_payload.append({"time": ts, "value": unit})

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
        f"Market overview for {term}:\n"
        f"- {len(chart_payload)} points over last 30d\n"
        f"- Active suppliers: {suppliers_count}\n"
        f"- Volume last 30d: {volumes_sum:.0f} kg\n"
        f"- Headlines: {headlines}\n\n"
        "Summarize in clear bullet points."
    )

    try:
        resp = _chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=300,
        )
        analysis = _choice_content(resp)
    except Exception as e:
        analysis = f"⚠️ LLM error: {e}"

    return {
        "analysisText": analysis,
        "visualPayload": {
            "products": products_payload,
            "chartData": chart_payload,
            "suppliers": suppliers_count,
            "volumes": float(volumes_sum or 0),
        },
    }