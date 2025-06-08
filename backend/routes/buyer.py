# File: backend/routes/buyer.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.deal import Deal  # or wherever you compute metrics
from ..models.product import Product

router = APIRouter(prefix="/api/buyer", tags=["Buyer"])

@router.get("/dashboard")
def buyer_dashboard(db: Session = Depends(get_db)):
    # TODO: replace with real logic
    total_sales = 0
    open_orders  = 0
    pending_esc  = 0
    available    = db.query(Product).count()
    active_deals = db.query(Deal).filter(Deal.status=="active").count()

    return {
      "totalSalesToday": total_sales,
      "openOrders":       open_orders,
      "pendingEscrow":    pending_esc,
      "availableProducts": available,
      "activeDeals":      active_deals,
    }