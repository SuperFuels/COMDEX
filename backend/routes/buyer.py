# File: backend/routes/buyer.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.deal import Deal
from ..models.product import Product
from ..models.user import User
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/buyer", tags=["Buyer"])

@router.get("/dashboard")
def buyer_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session       = Depends(get_db),
):
    """
    Buyer dashboard metrics:
      - totalSalesToday
      - openOrders
      - pendingEscrow
      - availableProducts
      - activeDeals
    """
    # 1) Ensure only buyers can access
    if current_user.role != "buyer":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Only buyers can access this endpoint"
        )

    # 2) TODO: Replace with real calculations
    total_sales     = 0
    open_orders     = 0
    pending_escrow  = 0

    # Available products = count of all products in the marketplace
    available = db.query(Product).count()

    # Active deals where this user is the buyer
    active_deals = (
        db.query(Deal)
          .filter(Deal.buyer_id == current_user.id, Deal.status == "active")
          .count()
    )

    return {
        "totalSalesToday":   total_sales,
        "openOrders":        open_orders,
        "pendingEscrow":     pending_escrow,
        "availableProducts": available,
        "activeDeals":       active_deals,
    }