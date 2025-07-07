# File: backend/routes/buyer.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import Base, engine, get_db
from backend.models.deal import Deal
from backend.models.product import Product
from backend.models.user import User
from backend.utils.auth import get_current_user

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

router = APIRouter(
    prefix="/buyer",
    tags=["Buyer"],
)

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
    # 1) Only buyers may call this
    if current_user.role != "buyer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only buyers can access this endpoint"
        )

    # 2) Stub data – replace with real logic as needed
    total_sales     = 0
    open_orders     = 0
    pending_escrow  = 0

    # Available products in marketplace
    available_products = db.query(Product).count()

    # Active deals for this buyer
    active_deals = (
        db.query(Deal)
          .filter(Deal.buyer_id == current_user.id, Deal.status == "active")
          .count()
    )

    return {
        "totalSalesToday":   total_sales,
        "openOrders":        open_orders,
        "pendingEscrow":     pending_escrow,
        "availableProducts": available_products,
        "activeDeals":       active_deals,
    }